from datetime import datetime

from django.utils.translation import gettext as _
from django.db import transaction

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from user.models import (
    User,
    Sportsman,
    Trainer,
    Media,
    Education,
    Result,
    School
)

from dashboard.models import (
    Tournament, 
    Sport,
    Team
)

from .models import PrivacyPolicy, TermsOfCondition

from shared.addons.custom_logging import logger
from shared.addons.exceptions import raise_validation_error
from shared.addons.utils import CorrectPath


class InlineMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = [
            "id",
            "media_type",
            "file",
            "size",
            "extension",
        ]


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "email",
            "user_role",
            "created_time",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.user_role == "sportsman":
            if instance.sportsman_profile and instance.sportsman_profile.trainer:
                data["trainer_id"] = instance.sportsman_profile.trainer.user.id
                data["trainer_name"] = f'{instance.sportsman_profile.trainer.user}'
        return data


class SportsmanExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sportsman
        fields = [
            "height",
            "weight",
            "region",
            "city",
            "street",
            "citizenship",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.trainer:
            data["trainer_name"] = f'{instance.trainer.user}'
        if instance.sport:
            data["sport"] = instance.sport.name
        return data


class TrainerExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trainer
        fields = [
            "height",
            "weight",
            "region",
            "city",
            "street",
            "citizenship",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.sport:
            data["sport"] = instance.sport.name
        return data


class UserExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "email",
            "user_role",
            "birth_date",
            "created_time",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        if instance.user_role == "sportsman":
            sportsman_data = SportsmanExportSerializer(instance.sportsman_profile).data
            data.update(sportsman_data)  # Merge sportsman data into the main data

        elif instance.user_role == "trainer":
            trainer_data = TrainerExportSerializer(instance.trainer_profile).data
            data.update(trainer_data)  # Merge trainer data into the main data

        return data


class SportCreateSerializer(serializers.ModelSerializer):
    logo = InlineMediaSerializer(many=True, read_only=True)
    logo_id = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)

    class Meta:
        model = Sport
        fields = (
            "id",
            "name",
            "logo_id",
            "logo",
        )
        extra_kwargs = {"id": {"read_only": True}, "logo": {"required": False}}

    def update(self, instance, validated_data):
        logo_id = validated_data.pop("logo_id", None)
        if logo_id:
            media_object = Media.objects.filter(id__in=logo_id)
            if not media_object.exists():
                raise_validation_error(message=_("At least one media must be uploaded"))
            current_logos = instance.logo.all() # Get the current logos
            logo_to_delete = current_logos.exclude(id__in=logo_id)
            for logo in logo_to_delete:
                instance.logo.remove(logo)
                logo.file.delete()  # Delete the file from the file system
                logo.delete()  # Delete the Media object from the database
            
            instance.logo.set(media_object)
        else:
            current_logos = instance.logo.all()
            for logo in current_logos:
                instance.logo.remove(logo)
                logo.file.delete()
                logo.delete()
            instance.logo.clear()

        return super().update(instance, validated_data)

    def create(self, validated_data):
        sport = Sport.objects.filter(name=validated_data["name"]).first()
        sport_name = validated_data["name"]
        if sport:
            raise_validation_error(message=_(f"{sport_name} - sport is already created"))

        logo_id = validated_data.pop("logo_id", None)
        sport = Sport.objects.create(**validated_data)

        if logo_id:
            media_object = Media.objects.filter(id__in=logo_id)
            sport.logo.set(media_object)
        return sport


class SportSerializer(serializers.ModelSerializer):
    logo = InlineMediaSerializer(many=True, read_only=True)
    
    class Meta:
        model = Sport
        fields = (
            "id",
            "name",
            "logo",
        )


class TournamentCreateSerializer(serializers.ModelSerializer):
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source='sport', write_only=True)
    logo_id = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    logo = InlineMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "start_time",
            "place",
            "division",
            "sport_id",
            "logo_id",
            "logo",
        )
        extra_kwargs = {"id": {"read_only": True}, "logo": {"required": False}}
    
    def validate(self, attrs):
        name = attrs.get("name", None)
        start_time = attrs.get("start_time", None)
        instance = self.instance  # This will be None during creation and the instance during updating
        new_year = start_time.year
        print(new_year)

        if instance:  # Only for updates
            current_name = instance.name
            current_year = instance.start_time.year
            print(f"current_year: {current_year}")

            # Check if the name or year is being updated
            is_name_updated = name is not None and name != current_name
            is_year_updated = new_year is not None and new_year != current_year

            # If either name or year is being updated, perform the uniqueness check
            if is_name_updated or is_year_updated:
                queryset = Tournament.objects.filter(name=name, start_time__year=new_year)
                queryset = queryset.exclude(id=instance.id)  # Exclude the current instance

                if queryset.exists():
                    raise_validation_error(_("Tournament with this name and year already exists!"))
        
        else:  # For creation
            if name and new_year:
                queryset = Tournament.objects.filter(name=name, start_time__year=new_year)
                if queryset.exists():
                    raise_validation_error(_("Tournament with this name and year already exists!"))
        
        return attrs

    def update(self, instance, validated_data):
        logo_id = validated_data.pop("logo_id", None)
        
        if logo_id:
            media_object = Media.objects.filter(id__in=logo_id)
            if not media_object.exists():
                raise_validation_error(message=_("At least one media must be uploaded"))
            current_logos = instance.logo.all() # Get the current logos
            logo_to_delete = current_logos.exclude(id__in=logo_id)
            
            for logo in logo_to_delete:
                instance.logo.remove(logo)
                logo.file.delete()
                logo.delete()
            
            instance.logo.set(media_object)
        else:
            current_logos = instance.logo.all()
            for logo in current_logos:
                instance.logo.remove(logo)
                logo.file.delete()
                logo.delete()
            instance.logo.clear()

        return super().update(instance, validated_data)
    
    def create(self, validated_data):
        sport = validated_data.pop("sport")
        logo_id = validated_data.pop("logo_id", None)
        tournament = Tournament.objects.create(sport=sport, **validated_data)
        if logo_id:
            media_object = Media.objects.filter(id__in=logo_id)
            tournament.logo.set(media_object)
        return tournament

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_name"] = instance.sport.name
        return data


class TournamentSerializer(serializers.ModelSerializer):
    sport = SportSerializer(many=False)
    logo = InlineMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "start_time",
            "place",
            "division",
            "sport",
            "logo",
        )


class TeamCreateSerializer(serializers.ModelSerializer):
    logo = InlineMediaSerializer(many=True, read_only=True)
    logo_id = serializers.UUIDField(format='hex_verbose', write_only=True, required=False)
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source='sport', write_only=True)
    member_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=True)

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "logo",
            "logo_id",
            "sport_id",
            "founded_year",
            "member_ids",
            "social_media",
            "wins",
            "losses",
            "draws",
        )
        extra_kwargs = {"id": {"read_only": True}, "wins": {"required": False}, "losses": {"required": False}, "draws": {"required": False}}
    
    def validate(self, attrs):
        founded_year = attrs.get("founded_year", None)
        name = attrs.get("name", None)
        team = Team.objects.filter(name=name).first()
        if team:
            raise_validation_error(message=_("Team with name already created"))

        current_year = datetime.now().year
        if founded_year and founded_year > current_year:
            raise_validation_error(message=_("Founded year must be less than current year"))
        
        return attrs

    def create(self, validated_data):
        sport = validated_data.pop("sport")
        logo_id = validated_data.pop("logo_id", None)
        member_ids = validated_data.pop("member_ids")

        team = Team.objects.create(sport=sport, **validated_data)

        if logo_id:
            media_object = Media.objects.get(id=logo_id)
            team.logo.add(media_object)
        
        if member_ids:
            member_objects = User.objects.filter(id__in=member_ids)
            team.members.set(member_objects)
        
        return team
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sport_id"] = instance.sport.id
        data["sport_name"] = instance.sport.name 
        logger.info(f"Members: {instance.members}")
        data["members"] = UserListSerializer(
            [member for member in instance.members.all()],
            many=True,
        ).data
        return data
    

class TeamUpdateSerializer(TeamCreateSerializer):
    logo = InlineMediaSerializer(many=True, read_only=True)
    logo_id = serializers.UUIDField(format='hex_verbose', write_only=True, required=False)
    sport_id = serializers.PrimaryKeyRelatedField(queryset=Sport.objects.all(), source='sport', write_only=True, required=False)
    member_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)

    class Meta(TeamCreateSerializer.Meta):
        extra_kwargs = {
            **TeamCreateSerializer.Meta.extra_kwargs, 
        }
    
    def update(self, instance, validated_data):
        logo_id = validated_data.pop("logo_id", None) # m-t-m
        member_ids = validated_data.pop("member_ids", None) # m-t-m

        # Update basic team fields
        for attrs, value in validated_data.items():
            setattr(instance, attrs, value)
        instance.save()

        if member_ids:
            member_objects = User.objects.filter(id__in=member_ids)
            instance.members.set(member_objects)
        
        if logo_id:
            media_object = Media.objects.filter(id__in=logo_id)
            if not media_object.exists():
                raise_validation_error(message=_("At least one media must be uploaded"))
            current_logos = instance.logo.all() # Get the current logos
            logo_to_delete = current_logos.exclude(id__in=logo_id)
            
            for logo in logo_to_delete:
                instance.logo.remove(logo)
                logo.file.delete()
                logo.delete()
            
            instance.logo.set(media_object)
        else:
            current_logos = instance.logo.all()
            for logo in current_logos:
                instance.logo.remove(logo)
                logo.file.delete()
                logo.delete()
            instance.logo.clear()

        return instance


class TeamSerializer(serializers.ModelSerializer):
    logo = InlineMediaSerializer(many=True)
    sport = SportSerializer()
    members = UserListSerializer(many=True)

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "sport",
            "founded_year",
            "logo",
            "members",
            "social_media",
            "wins",
            "losses",
            "draws",
        ]


class SchoolCreateSerializer(serializers.ModelSerializer):
    sport_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=True)
    sports = SportSerializer(many=True, required=False)

    class Meta:
        model = School
        fields = [
            "id",
            "name",
            "phone_number",
            "director",
            "type",
            "address",
            "sport_ids",
            "sports"
        ]
        extra_kwargs = {"id": {"read_only": True},}

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")
        
        if School.objects.filter(phone_number=phone_number).exists():
            raise_validation_error(message=_("Phone number is already registered"))
        
        return attrs

    def create(self, validated_data):
        sport_ids = validated_data.pop("sport_ids", None)
        
        with transaction.atomic():
            school = School.objects.create(**validated_data)

            if sport_ids:
                sport_objects = Sport.objects.filter(id__in=sport_ids)
                if not sport_objects.exists():
                    raise_validation_error(message=_(f"At least one sport must be included"))
                school.sports.set(sport_objects)
            
        return school


class SchoolUpdateSerializer(SchoolCreateSerializer):
    sport_ids = serializers.ListField(child=serializers.UUIDField(format='hex_verbose'), write_only=True, required=False)
    
    class Meta(SchoolCreateSerializer.Meta):
        extra_kwargs = {
            **SchoolCreateSerializer.Meta.extra_kwargs,
        }
    
    def validate(self, attrs):
        phone_number = attrs.get("phone_number")

        if phone_number and self.instance.phone_number != phone_number:
            if School.objects.filter(phone_number=phone_number).exists():
                raise_validation_error(message=_("Phone number is already registered"))

        return attrs
    
    def update(self, instance, validated_data):
        sport_ids = validated_data.pop("sport_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if sport_ids:
            sport_objects = Sport.objects.filter(id__in=sport_ids)
            if not sport_objects.exists():
                raise_validation_error(message=_("At least one sport must be included"))
            instance.sports.set(sport_objects)

        return instance
    

class SchoolSerializer(serializers.ModelSerializer):
    sports = SportSerializer(many=True)

    class Meta:
        model = School
        fields = [
            "id",
            "name",
            "phone_number",
            "director",
            "type",
            "address",
            "sports",
        ]


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = ("id", "title", "language", "text")

    def validate(self, attrs):
        language = attrs.get('language')
        instance = self.instance

        if instance:
            current_language = instance.language
            is_language_updated = language is not None and language != current_language

            if is_language_updated:                
                queryset = PrivacyPolicy.objects.filter(language=language)
                queryset = queryset.exclude(id=instance.id)

                if queryset.exists():
                    raise_validation_error(_("Privacy Policy with this language already exists"))
        else:
            if language:
                if PrivacyPolicy.objects.filter(language=language).exists():
                    raise_validation_error(message=_("Privacy Policy with this language already exists"))

        return attrs


class TermsOfConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsOfCondition
        fields = ("id", "title", "language", "text")

    def validate(self, attrs):
        language = attrs.get("language")
        instance = self.instance

        if instance:
            current_language = instance.language
            is_language_updated = language is not None and language != current_language

            if is_language_updated:
                queryset = TermsOfCondition.objects.filter(language=language)
                queryset.exclude(id=instance.id)

                if queryset.exists():
                    raise_validation_error(_("Terms of Conditions with language already exists"))
        else:
            if language:
                if TermsOfCondition.objects.filter(language=language).exists():
                    raise_validation_error(message=_("Terms of Conditions with this language already exists"))
            
        return attrs