from import_export import fields, resources, widgets

from .models import (
    AuthorizationProfile,
    BlueprintPermission,
    Role,
    User,
    UserAuthorizationProfile,
)


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        import_id_fields = ("username",)
        fields = (
            "date_joined",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "recently_viewed",
            "uuid",
            "username",
        )
        skip_unchanged = True


class RoleResource(resources.ModelResource):
    class Meta:
        model = Role
        import_id_fields = ("name",)
        fields = ("name", "permissions")


class BlueprintPermissionResource(resources.ModelResource):
    role = fields.Field(
        column_name="role",
        attribute="role",
        widget=widgets.ForeignKeyWidget(Role, field="name"),
    )

    class Meta:
        model = BlueprintPermission
        import_id_fields = ("hashkey",)
        fields = (
            "hashkey",
            "object_type",
            "role",
            "policy",
        )


class AuthorizationProfileResource(resources.ModelResource):
    blueprint_permissions = fields.Field(
        column_name="blueprint_permissions",
        attribute="blueprint_permissions",
        widget=widgets.ManyToManyWidget(
            BlueprintPermission, field="hashkey", separator="|"
        ),
    )

    class Meta:
        model = AuthorizationProfile
        import_id_fields = ("name",)
        fields = ("uuid", "name", "blueprint_permissions")


class UserAuthorizationProfileResource(resources.ModelResource):
    user = fields.Field(
        column_name="user",
        attribute="user",
        widget=widgets.ForeignKeyWidget(User, field="username"),
    )
    auth_profile = fields.Field(
        column_name="auth_profile",
        attribute="auth_profile",
        widget=widgets.ForeignKeyWidget(AuthorizationProfile, field="uuid"),
    )

    class Meta:
        model = UserAuthorizationProfile
        import_id_fields = ("user", "auth_profile")
        fields = ("user", "auth_profile", "start", "end")
