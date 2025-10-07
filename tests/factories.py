import factory
from django.apps import apps

User = apps.get_model('user', 'User')
Sportsman = apps.get_model('user', 'Sportsman')
Trainer = apps.get_model('user', 'Trainer')
ArchivedTrainer = apps.get_model('user', 'ArchivedTrainer')

Sport = apps.get_model('sport', 'Sport')
Result = apps.get_model('sport', 'Result')
Tournament = apps.get_model('sport', 'Tournament')

Education = apps.get_model('career', 'Education')
School = apps.get_model('sport', 'School')


class SportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sport

    name = factory.Faker('word')
    logo = factory.django.ImageField(
        color="blue",
        width=800,
        height=800,
        format="JPEG"
    )


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker("first_name")
    middle_name = factory.Faker("middle_name")
    last_name = factory.Faker("last_name")

    pinfl = factory.Sequence(lambda n: f"{n:014d}")
    gender = "male"
    user_role = "sportsman"
    phone_number = factory.Sequence(lambda n: f"+998{n:09d}")
    email = factory.Faker("email")
    birth_date = factory.Faker("date")


class TrainerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Trainer

    user = factory.SubFactory(UserFactory)
    sport = factory.SubFactory(SportFactory)

    skill_level = factory.Faker("word")
    bio = factory.Faker("sentence")
    division = factory.Faker("random_int", min=1, max=10)
    user_metrics = factory.Dict({})
    address = factory.Dict({})
    social_media = factory.Dict({})


class SportsmanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sportsman

    user = factory.SubFactory(UserFactory)
    sport = factory.SubFactory(SportFactory)
    trainer = factory.SubFactory(TrainerFactory)

    skill_level = factory.Faker("word")
    bio = factory.Faker("sentence")
    division = factory.Faker("random_int", min=1, max=10)
    user_metrics = factory.Dict({})
    address = factory.Dict({})
    social_media = factory.Dict({})


class ArchivedTrainerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ArchivedTrainer

    name = factory.Faker("word")


class TournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tournament

    name = factory.Faker('word')
    start_time = factory.Faker('date')
    place = factory.Faker('country')
    division = factory.Faker('random_int', min=1, max=10)
    sport = factory.SubFactory(SportFactory)
    logo = factory.django.ImageField(
        color="yellow",
        width=800,
        height=800,
        format="JPEG"
    )


class ResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Result

    country = factory.Faker('country')
    year = factory.Faker('random_int', min=2000, max=2024)
    currently_participating = True

    user = factory.SubFactory(UserFactory)
    trainer = factory.SubFactory(TrainerFactory)
    archived_trainer = factory.SubFactory(ArchivedTrainerFactory)

    tournament = factory.SubFactory(TournamentFactory)
    additional_attributes = factory.Dict({})

    rating = factory.Faker('random_int', min=1, max=3)


class SchoolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = School

    name = factory.Faker('word')
    phone_number = factory.Sequence(lambda n: f"+998{n:09d}")
    director = factory.Faker('word')

    address = factory.Dict({})
    type = "ordinary"
    sports = factory.RelatedFactoryList(SportFactory, size=2) # Create 2 related Sport objects


class EducationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Education

    sport = factory.SubFactory(SportFactory)
    start_year = factory.Faker("random_int", min=2000, max=2010)
    end_year = factory.Faker("number_int", min=2011, max=2023)
    currently_studying = "True"

    school = factory.SubFactory(SchoolFactory)
    user = factory.SubFactory(UserFactory)
