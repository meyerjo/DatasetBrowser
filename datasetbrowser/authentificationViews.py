import logging
import os

import jsonpickle
from pyramid.httpexceptions import HTTPFound
from pyramid.security import forget, remember
from pyramid.view import view_config, forbidden_view_config

from datasetbrowser.requesthandler.directoryRequestHandler import DirectoryRequestHandler
from datasetbrowser.requesthandler.fileHandler import open_resource


class AuthentificationViews:

    def __init__(self, request):
        self.request = request
        self.logged_in = request.authenticated_userid

    @view_config(route_name='login', renderer='template/login.pt')
    @forbidden_view_config(renderer='template/login.pt')
    def login(self):
        login_url = self.request.resource_url(self.request.context, 'login')
        referrer = self.request.url
        if referrer == login_url:
            referrer = '/'  # never use the login form itself as came_from
        came_from = self.request.params.get('came_from', referrer)
        message = ''
        login = ''
        password = ''
        if 'form.submitted' in self.request.params:
            login = self.request.params['login']
            password = self.request.params['password']
            usermanager = self.request.registry.settings['usermanager']

            if usermanager.validate_password(login, password):
                headers = remember(self.request, login)
                return HTTPFound(location=came_from,
                                 headers=headers)
            message = 'Failed login'

        description_is_private = False
        if 'privacy.description' in self.request.registry.settings:
            description_is_private = self.request.registry.settings['privacy.description'] == 'private'

        # load the information
        try:
            relative_path = DirectoryRequestHandler.requestfolderpath(self.request)
            description = os.path.join(relative_path, '.description.json')
            if not os.path.exists(description) or description_is_private:
                information = None
            else:
                with open_resource(description) as file:
                    json_file = file.read()
                    description_obj = jsonpickle.decode(json_file)
                    information = description_obj['shortdescription']
        except BaseException as e:
            information = 'Error: {0}'.format(e.message)
            log = logging.getLogger(__name__)
            log.error(e.message)


        return dict(
            message=message,
            url=self.request.application_url + '/login',
            came_from=came_from,
            login=login,
            password=password,
            information=information
        )

    @view_config(route_name='logout')
    def logout(self):
        headers = forget(self.request)
        return HTTPFound(location=self.request.resource_url(self.request.context),
                         headers=headers)

    @view_config(route_name='usermanagement', renderer='template/usermanagement.pt', permission='nooneshouldhavethispermission')
    def usermanagement(self):
        log = logging.getLogger(__name__)

        users = self.request.registry.settings['usermanager'].allUsers()
        aclgroups = self.request.root.get_all_groups()
        renderdict =  dict(folders=[], files=dict(),
                           logged_in=self.logged_in, users=users,
                           request=self.request, aclgroups=aclgroups,
                           error=None)
        return renderdict


    @view_config(route_name='usermanagement_action', renderer='json', permission='nooneshouldhavethispermission', match_param="action=updateuser")
    def updateuser(self):
        log = logging.getLogger(__name__)
        matchdict = self.request.matchdict
        params = dict(self.request.params)

        if 'roles' in params and isinstance(params['roles'], unicode):
            params['roles'] = jsonpickle.decode(params['roles'])

        try:
            log.info('Update user {0}'.format(matchdict['id']))
            self.request.registry.settings['usermanager'].update_user(matchdict['id'],
                                                                      params['username'],
                                                                      params['useractive'],
                                                                      params['roles'])
            return {'error': None}
        except BaseException as e:
            log.warning(e.message)
            return {'error': str(e.message)}


    @view_config(route_name='usermanagement_action', renderer='json', permission='nooneshouldhavethispermission', match_param="action=deleteuser")
    def deleteuser(self):
        log = logging.getLogger(__name__)
        matchdict = self.request.matchdict
        params = dict(self.request.params)

        if 'roles' in params and isinstance(params['roles'], unicode):
            params['roles'] = jsonpickle.decode(params['roles'])

        if matchdict['id'] == params['username']:
            try:
                log.info('Delete user: {0}'.format(matchdict['id']))
                self.request.registry.settings['usermanager'].delete_user(matchdict['id'])
                return dict(error=None)
            except BaseException as e:
                log.warning(e.message)
                error = str(e.message)
                return dict(error=error)
        return dict(error='Names do not match {0} != {1}'.format(matchdict['id'], params['username']))

    @view_config(route_name='usermanagement_action', renderer='json', permission='nooneshouldhavethispermission',
                     match_param="action=adduser")
    def adduser(self):
        log = logging.getLogger(__name__)
        matchdict = self.request.matchdict
        params = dict(self.request.params)

        if 'roles' in params and isinstance(params['roles'], unicode):
            params['roles'] = jsonpickle.decode(params['roles'])

        if matchdict['id'] == 'newuser':
            try:
                log.info('Try to add user "{0}" now'.format(params['username']))
                self.request.registry.settings['usermanager'].add_user(params['username'],
                                                                       params['username'].lower(),
                                                                       params['useractive'],
                                                                       params['roles'])
                return dict(error=None)
            except BaseException as e:
                log.warning(e.message)
                error = str(e.message)
                return dict(error=error)
        return dict(error='Invalid matchdict[id] field: {0}'.format(matchdict['id']))

    @view_config(route_name='usermanagement_action', renderer='json', permission='nooneshouldhavethispermission')
    def dummy(self):
        return dict(error='Match param field didnt match any expecations')
