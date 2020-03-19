"""Organization patching support."""

import logging

import bson
from flask import Blueprint, jsonify
import werkzeug.exceptions as wz_exceptions

from pillar.api.utils.authentication import current_user
from pillar.api.utils import authorization, str2id, jsonify
from pillar.api import patch_handler
from pillar import current_app

log = logging.getLogger(__name__)
patch_api_blueprint = Blueprint('pillar.api.organizations.patch', __name__)


class OrganizationPatchHandler(patch_handler.AbstractPatchHandler):
    item_name = 'organization'

    @authorization.require_login()
    def patch_assign_users(self, org_id: bson.ObjectId, patch: dict):
        """Assigns users to an organization.

        The calling user must be admin of the organization.
        """
        from . import NotEnoughSeats

        self._assert_is_admin(org_id)

        # Do some basic validation.
        try:
            emails = patch['emails']
        except KeyError:
            raise wz_exceptions.BadRequest('No key "email" in patch.')

        # Skip empty emails.
        emails = [stripped
                  for stripped in (email.strip() for email in emails)
                  if stripped]

        log.info('User %s uses PATCH to add users to organization %s',
                 current_user().user_id, org_id)
        try:
            org_doc = current_app.org_manager.assign_users(org_id, emails)
        except NotEnoughSeats:
            resp = jsonify({'_message': f'Not enough seats to assign {len(emails)} users'})
            resp.status_code = 422
            return resp

        return jsonify(org_doc)

    @authorization.require_login()
    def patch_assign_user(self, org_id: bson.ObjectId, patch: dict):
        """Assigns a single user by User ID to an organization.

        The calling user must be admin of the organization.
        """
        from . import NotEnoughSeats
        self._assert_is_admin(org_id)

        # Do some basic validation.
        try:
            user_id = patch['user_id']
        except KeyError:
            raise wz_exceptions.BadRequest('No key "user_id" in patch.')

        user_oid = str2id(user_id)
        log.info('User %s uses PATCH to add user %s to organization %s',
                 current_user().user_id, user_oid, org_id)
        try:
            org_doc = current_app.org_manager.assign_single_user(org_id, user_id=user_oid)
        except NotEnoughSeats:
            resp = jsonify({'_message': f'Not enough seats to assign this user'})
            resp.status_code = 422
            return resp

        return jsonify(org_doc)

    @authorization.require_login()
    def patch_assign_admin(self, org_id: bson.ObjectId, patch: dict):
        """Assigns a single user by User ID as admin of the organization.

        The calling user must be admin of the organization.
        """

        self._assert_is_admin(org_id)

        # Do some basic validation.
        try:
            user_id = patch['user_id']
        except KeyError:
            raise wz_exceptions.BadRequest('No key "user_id" in patch.')

        user_oid = str2id(user_id)
        log.info('User %s uses PATCH to set user %s as admin for organization %s',
                 current_user().user_id, user_oid, org_id)
        current_app.org_manager.assign_admin(org_id, user_id=user_oid)

    @authorization.require_login()
    def patch_remove_user(self, org_id: bson.ObjectId, patch: dict):
        """Removes a user from an organization.

        The calling user must be admin of the organization.
        """

        # Do some basic validation.
        email = patch.get('email') or None
        user_id = patch.get('user_id')
        user_oid = str2id(user_id) if user_id else None

        # Users require admin rights on the org, except when removing themselves.
        current_user_id = current_user().user_id
        if user_oid is None or user_oid != current_user_id:
            self._assert_is_admin(org_id)

        log.info('User %s uses PATCH to remove user %s from organization %s',
                 current_user_id, user_oid, org_id)

        org_doc = current_app.org_manager.remove_user(org_id, user_id=user_oid, email=email)
        return jsonify(org_doc)

    def _assert_is_admin(self, org_id):
        om = current_app.org_manager

        if current_user().has_cap('admin'):
            # Always allow admins to edit every organization.
            return

        if not om.user_is_admin(org_id):
            log.warning('User %s uses PATCH to edit organization %s, '
                        'but is not admin of that Organization. Request denied.',
                        current_user().user_id, org_id)
            raise wz_exceptions.Forbidden()

    @authorization.require_login()
    def patch_edit_from_web(self, org_id: bson.ObjectId, patch: dict):
        """Updates Organization fields from the web.

        The PATCH command supports the following payload. The 'name' field must
        be set, all other fields are optional. When an optional field is
        ommitted it will be handled as an instruction to clear that field.
            {'name': str,
             'description': str,
             'website': str,
             'location': str,
             'ip_ranges': list of human-readable IP ranges}
        """

        from pymongo.results import UpdateResult
        from . import ip_ranges

        self._assert_is_admin(org_id)
        user = current_user()
        current_user_id = user.user_id

        # Only take known fields from the patch, don't just copy everything.
        update = {
            'name': patch['name'].strip(),
            'description': patch.get('description', '').strip(),
            'website': patch.get('website', '').strip(),
            'location': patch.get('location', '').strip(),
        }
        unset = {}

        # Special transformation for IP ranges
        iprs = patch.get('ip_ranges')
        if iprs:
            ipr_docs = []
            for r in iprs:
                try:
                    doc = ip_ranges.doc(r, min_prefixlen6=48, min_prefixlen4=8)
                except ValueError as ex:
                    raise wz_exceptions.UnprocessableEntity(f'Invalid IP range {r!r}: {ex}')
                ipr_docs.append(doc)
            update['ip_ranges'] = ipr_docs
        else:
            unset['ip_ranges'] = True

        refresh_user_roles = False
        if user.has_cap('admin'):
            if 'seat_count' in patch:
                update['seat_count'] = int(patch['seat_count'])
            if 'org_roles' in patch:
                org_roles = [stripped for stripped in (role.strip() for role in patch['org_roles'])
                             if stripped]
                if not all(role.startswith('org-') for role in org_roles):
                    raise wz_exceptions.UnprocessableEntity(
                        'Invalid role given, all roles must start with "org-"')

                update['org_roles'] = org_roles
                refresh_user_roles = True

        self.log.info('User %s edits Organization %s: %s', current_user_id, org_id, update)

        validator = current_app.validator_for_resource('organizations')
        if not validator.validate_update(update, org_id, persisted_document={}):
            resp = jsonify({
                '_errors': validator.errors,
                '_message': ', '.join(f'{field}: {error}'
                                      for field, error in validator.errors.items()),
            })
            resp.status_code = 422
            return resp

        # Figure out what to set and what to unset
        for_mongo = {'$set': update}
        if unset:
            for_mongo['$unset'] = unset

        organizations_coll = current_app.db('organizations')
        result: UpdateResult = organizations_coll.update_one({'_id': org_id}, for_mongo)

        if result.matched_count != 1:
            self.log.warning('User %s edits Organization %s but update matched %i items',
                             current_user_id, org_id, result.matched_count)
            raise wz_exceptions.BadRequest()

        if refresh_user_roles:
            self.log.info('Organization roles set for org %s, refreshing users', org_id)
            current_app.org_manager.refresh_all_user_roles(org_id)

        return '', 204


def setup_app(app):
    OrganizationPatchHandler(patch_api_blueprint)
    app.register_api_blueprint(patch_api_blueprint, url_prefix='/organizations')
