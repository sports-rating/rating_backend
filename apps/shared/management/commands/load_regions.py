import requests
from datetime import datetime

from django.core.management.base import BaseCommand
from apps.shared.models import Region, District, Neighborhood
from apps.shared.utils.logging import logger


class Command(BaseCommand):
    help = "A command to load regions and districts to the DB"

    def handle(self, *args, **kwargs):
        logger.info("In progress...")
        print("In progress...")

        start_time = datetime.now()

        # Define the region names
        region_names = [
            "Andijon viloyati", "Buxoro viloyati", "Jizzax viloyati",
            "Qashqadaryo viloyati", "Navoiy viloyati", "Namangan viloyati",
            "Samarqand viloyati", "Surxondaryo viloyati", "Sirdaryo viloyati",
            "Toshkent shahri", "Toshkent viloyati", "Farg‘ona viloyati",
            "Xorazm viloyati", "Qoraqalpog‘iston Respublikasi",
        ]

        regions = [Region(name=region_name) for region_name in region_names]
        Region.objects.bulk_create(regions, ignore_conflicts=True)

        limit = 1000

        for region in Region.objects.all():
            offset = 0
            while True:
                response = requests.get(
                    url="https://cs.egov.uz/apiPartner/Table/Get",
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    },
                    params={
                        "accessToken": "67a48e9d043b9345120892b2",
                        "name": "035-3-004",
                        "limit": limit,
                        "offset": offset,
                        "lang": 1
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Failed to fetch data for region {region.name}")
                    break

                response_json = response.json()
                data = response_json.get("result", {}).get("data", [])

                if not data:
                    break  # Stop pagination if there's no more data

                for item in data:
                    if not isinstance(item, dict):
                        continue

                    if item.get("Region") == region.name:
                        district_name = item.get("District")
                        neighborhood_name = item.get("Name")

                        if district_name and neighborhood_name:
                            district, _ = District.objects.get_or_create(
                                name=district_name,
                                region=region
                            )
                            Neighborhood.objects.get_or_create(
                                name=neighborhood_name,
                                district=district
                            )

                offset += limit  # Move to the next batch

        end_time = datetime.now()
        duration = end_time - start_time

        logger.info(f"Done in {duration.total_seconds()} seconds")
        print(f"Done in {duration.total_seconds()} seconds")
