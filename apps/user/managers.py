from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The username must be set")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        extra_fields.setdefault("first_name", "Admin_B")
        extra_fields.setdefault("last_name", "Admin_B")
        extra_fields.setdefault("user_role", "super_admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if extra_fields.get("user_role") != "super_admin":
            raise ValueError("Superuser must have role of super_admin.")

        return self.create_user(username, password, **extra_fields)
