import logging
import mimetypes
import os
import re
import numpy
import sys
from Levenshtein._levenshtein import distance
from pyramid.renderers import render


class ItemGrouper:
    def __init__(self):
        pass

    @staticmethod
    def _compute_edit_distance_matrix(input):
        """
        Computes the edit distance between the
        :param input:
        :return:
        """
        assert(isinstance(input, list))
        matrix = numpy.zeros(shape=(len(input), len(input)))
        for i, item_a in enumerate(input):
            for j, item_b in enumerate(input):
                if i == j:
                    matrix[i, j] = sys.maxint - 1000
                else:
                    matrix[i, j] = distance(item_a, item_b)
        return matrix

    def _group_by_matrix(self, input, matrix, items_per_row):
        """
        Groups the elements in input into rows using the weights contained in matrix.
        :param input:
        :param matrix:
        :param items_per_row:
        :return:
        """
        rows = []
        tmp_row = []
        minvalue = matrix.min()
        elements_to_add = len(input)
        # TODO: refactor this, should be more pretty
        while minvalue != sys.maxint:
            index = numpy.unravel_index(matrix.argmin(), matrix.shape)
            elements = [input[index[0]], input[index[1]]]

            for element in elements:
                tmp_row.append(element)
                elements_to_add -= 1
                if len(tmp_row) == items_per_row:
                    rows.append(tmp_row)
                    tmp_row = []
                if elements_to_add == 0 and len(tmp_row) > 0:
                    rows.append(tmp_row)
                    tmp_row = []

            # prevent this tuple from further existing
            matrix[index] = sys.maxint
            matrix[index[1], index[0]] = sys.maxint

            # if the row is full then we can eliminate the files, otherwise we have to leave space for 
            if len(tmp_row) == 0:
                matrix[index[0], :] = sys.maxint
                matrix[index[1], :] = sys.maxint
                matrix[:, index[0]] = sys.maxint
                matrix[:, index[1]] = sys.maxint
            minvalue = matrix.min()
        return rows

    def _alphabetical_grouping(self, items, elements_per_group):
        """
        Groups the items alphabetically into rows
        :param items:
        :param elements_per_group:
        :return:
        """
        groups = []
        tmp_group = []
        for item in sorted(items):
            tmp_group.append(item)
            if len(tmp_group) == elements_per_group:
                groups.append(tmp_group)
                tmp_group = []
        if len(tmp_group) > 0:
            groups.append(tmp_group)
        return groups

    def _reorganize_files(self, files, specific_filter_criteria=None, blacklist=None):
        if not blacklist:
            blacklist = []
        if not specific_filter_criteria:
            specific_filter_criteria = []

        items_dict = dict()
        visible_items = []
        invisible_items = []

        for file in files:
            skip = False
            for rule in blacklist:
                if rule == '':
                    continue
                if re.search(rule, file) is not None:
                    skip = True
                    break
            if skip:
                continue

            filename, file_ext = os.path.splitext(file)
            if not file.startswith('.'):
                visible_items.append(file)
                handled_file = False
                # Filter for specific filter-criteria. Enables the user to specify for example regex:README.md$
                # as a filter criteria and define specific behaviour rules
                for specific_criteria in specific_filter_criteria:
                    possible_criteria_types = ['mimetype:', 'regex:']
                    for criteria_type in possible_criteria_types:
                        if specific_criteria.startswith(criteria_type):
                            truncated_criteria = specific_criteria[len(criteria_type):]
                            element_to_validate = file
                            if criteria_type == 'mimetype:':
                                element_to_validate = mimetypes.guess_type(file)[0]
                                if element_to_validate is None:
                                    continue
                            if re.search(truncated_criteria, element_to_validate) is not None:
                                if specific_criteria not in items_dict:
                                    items_dict[specific_criteria] = [file]
                                else:
                                    items_dict[specific_criteria].append(file)
                                handled_file = True
                                break
                    if handled_file:
                        break
                if handled_file:
                    continue

                # Unable to handle the file by specific criteria, thus we fall back to the fileextension
                if file_ext in items_dict:
                    items_dict[file_ext].append(file)
                else:
                    items_dict[file_ext] = [file]
            else:
                invisible_items.append(file)
        return items_dict, visible_items, invisible_items

    def _apply_filter_to_items(self, items, filter, is_last_filterrule=False):
        """
        Gets a list of string items and a list of filtercriteria consisting of regular_expressions and filters them into a dictionary
        :param items: list of strings
        :param filter: list of regular expressions
        :return: filtered dictionary
        """
        assert (isinstance(filter, str) or isinstance(filter, unicode))
        returning_dict = dict()
        for item in items:
            match = re.search(filter, item)
            if match is None:
                print('Couldn\'t group the following item, because the regex failed {0} {1}'.format(item, filter))
                continue
            if match.group() in returning_dict:
                returning_dict[match.group()].append(item)
            else:
                returning_dict[match.group()] = [item]
        return returning_dict

    def _filter_to_dict(self, items, filtercriteria):
        assert (len(filtercriteria) >= 1)
        returning_dict = dict()
        if isinstance(items, list):
            returning_dict = self._apply_filter_to_items(items, str(filtercriteria[0]), len(filtercriteria) == 1)
        if len(filtercriteria) == 1:
            return returning_dict

        for (key, values) in returning_dict.items():
            returning_dict[key] = self._filter_to_dict(values, filtercriteria[1:])
        return returning_dict

    def _split_files_into_subgroups(self, input, items_per_row, grouping_method='numerical'):
        assert (items_per_row >= 1)
        if isinstance(input, list):
            return self.group(input, items_per_row, grouping_method)
        elif isinstance(input, dict):
            for (key, value) in input.items():
                input[key] = self._split_files_into_subgroups(value, items_per_row, grouping_method)
            return input
        else:
            print('Something went wrong. The type of the input isn\'t a dict '
                  'or a list. {0}'.format(str(type(input))))
            return input

    def _group_files_by_specific_criteria(self, files, extension_specific):
        errors = []
        try:
            grouped_files = self._filter_to_dict(files, extension_specific['group_by'])
        except Exception as e:
            grouped_files = []
            errors.append(e.message)
        elements_per_row = extension_specific['elements_per_row']

        if 'grouping_method' not in extension_specific:
            row_group_files = self._split_files_into_subgroups(grouped_files, elements_per_row)
        else:
            row_group_files = self._split_files_into_subgroups(grouped_files, elements_per_row, extension_specific['grouping_method'])
        return row_group_files, errors

    def group(self, items, elements_per_group, method='numerical'):
        if method == 'alphabetical':
            return self._alphabetical_grouping(items, elements_per_group)
        elif method == 'numerical':
            matrix = self._compute_edit_distance_matrix(items)
            groups = self._group_by_matrix(items, matrix, elements_per_group)
            return groups
        else:
            return items

    def convert_leafs_to_dicts(self, tree, filespecific_updates=None):
        def _convert_list_to_listdict(l, filespecific_updates=None):
            if len(l) == 0:
                return l
            for i, item in enumerate(l):
                if isinstance(item, list):
                    l[i] = _convert_list_to_listdict(item, filespecific_updates)
                elif isinstance(item, str) or isinstance(item, unicode):
                    l[i] = dict(filename=item)
                    if filespecific_updates is None or not isinstance(filespecific_updates, dict):
                        continue
                    if item not in filespecific_updates:
                        continue
                    tmp_dict = filespecific_updates[item]
                    l[i].update(tmp_dict)
                else:
                    log = logging.getLogger(__name__)
                    log.warning('Unexpected element type in _convert_list_to {0}'.format(type(item)))
            return l

        if not isinstance(tree, dict):
            log = logging.getLogger(__name__)
            log.info('Type of tree is not dict, script will stop thus {0}: {1}'.format(type(tree)), tree)
            return tree
        for (key, value) in tree.items():
            if isinstance(value, dict):
                tree[key] = self.convert_leafs_to_dicts(value, filespecific_updates)
            elif isinstance(value, list):
                tree[key] = _convert_list_to_listdict(value, filespecific_updates)
        return tree

    def group_folder(self, files, directory_settings):
        # restructure files and split them according to their fileextension
        blacklist = None
        special_filter_criteria = None
        if 'blacklist' in directory_settings:
            blacklist = directory_settings['blacklist']
        if 'specific_filetemplates' in directory_settings:
            spec_ft = directory_settings['specific_filetemplates']
            if isinstance(spec_ft, dict):
                special_filter_criteria = spec_ft.keys()

        visible_items_by_extension, visible_items, invisible_items = \
            self._reorganize_files(files, special_filter_criteria, blacklist)

        visible_items_by_extension['..'] = ['..']

        # group the files by their individual
        for (extension, filenames) in visible_items_by_extension.items():
            if 'specific_filetemplates' not in directory_settings:
                continue
            if extension in directory_settings['specific_filetemplates']:
                extension_specific = directory_settings['specific_filetemplates'][extension]
                groupedfiles, errors = self._group_files_by_specific_criteria(filenames, extension_specific)
                visible_items_by_extension[extension] = groupedfiles

        return visible_items_by_extension, visible_items, invisible_items
