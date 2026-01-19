.. _authorization_import_export:

Authorization Import & Export
=============================

For time efficiency we allow the migration of authorization profiles. Currently a crude import and export
feature is built into the admin panel. Users wishing to migrate need to understand the architecture before
attempting an import and export. 

The importing of profiles is currently on an "upsert" basis (e.g., authorization profiles get updated or created). 
The order of import is crucial to a successful import and outlined explicitly here:

1. Roles
2. BlueprintPermissions (can/should be created through a management endpoint or command)
3. AuthorizationProfiles
4. Users (optional)
5. UserAuthorizationProfiles