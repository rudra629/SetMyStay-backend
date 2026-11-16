"""Sample listings so the site isn't empty: 10 PG, 10 rentals, 10 roommates with a place,
10 roommates looking for a place.

All of them belong to one locked account, "setmystay_samples" (it can't sign in).
To remove every sample listing later, delete that user in the Django admin or run:
    User.objects.filter(username='setmystay_samples').delete()
(Reversing this migration does the same.)

Contact number on every sample is the SetMyStay office number, so an unlock reaches the business.
Property photos: Unsplash (free to use). Profile pictures: DiceBear illustrated avatars (no real people).
"""
from datetime import timedelta

from django.db import migrations
from django.utils import timezone

SAMPLE_USERNAME = 'setmystay_samples'
OFFICE_PHONE = '7977169550'
OWNER = 'SetMyStay'


def u(photo_id):
    return f'https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=1200&q=75'


def avatar(name):
    from urllib.parse import quote
    return (f'https://api.dicebear.com/9.x/notionists/svg?seed={quote(name)}'
            '&backgroundColor=dbeafe,fde68a,fbcfe8,bbf7d0')


# Unsplash photos checked to load and to show rooms / buildings only
LIVING = [u('1505691938895-1758d7feb511'), u('1522708323590-d24dbb6b0267'), u('1502672260266-1c1ef2d93688'),
          u('1560448204-e02f11c3d0e2'), u('1493809842364-78817add7ffb'), u('1586023492125-27b2c045efd7'),
          u('1600210492486-724fe5c67fb0'), u('1513694203232-719a280e022f'), u('1560185007-cde436f6a4d0'),
          u('1617806118233-18e1de247200'), u('1630699144867-37acec97df5a'), u('1618221195710-dd6b41faaea6')]
BEDROOM = [u('1598928506311-c55ded91a20c'), u('1540518614846-7eded433c457'), u('1631049307264-da0ec9d70304'),
           u('1595526114035-0d45ed16cfbf'), u('1522771739844-6a9f6d5f14af'), u('1616594039964-ae9021a400a0'),
           u('1615874959474-d609969a20ed'), u('1617325247661-675ab4b64ae2')]
KITCHEN = [u('1484154218962-a197022b5858'), u('1560185893-a55cbc8c57e8'), u('1600607687939-ce8a6c25118c')]
BUILDING = [u('1545324418-cc1a3fa10c00'), u('1574362848149-11496d93a7c7'), u('1460317442991-0ec209397118'),
            u('1574362848149-11496d93a7c7'), u('1600047509807-ba8f99d2cdde'), u('1460317442991-0ec209397118')]


def pick(lst, i, n=1):
    return [lst[(i + k) % len(lst)] for k in range(n)]


PG = [
    # title, city, area, rent, room, furnishing, gender, sq_ft, amenities, description
    ('Boys PG near Andheri Station', 'Mumbai', 'Andheri East', 11000, 'Double Sharing', 'Furnished', 'Male', 180,
     ['Wi-Fi', 'AC', 'In-house Mess', 'Washing Machine (Private/Common)', 'Security'],
     '8 minutes walk from Andheri station. Two meals a day, weekly room cleaning and 24x7 water. Working professionals preferred.'),
    ('Girls PG with Meals in Powai', 'Mumbai', 'Powai', 14500, 'Single Room', 'Furnished', 'Female', 150,
     ['Wi-Fi', 'AC', 'In-house Mess', 'Security', 'Power Backup', 'Refrigerator'],
     'Private room close to Hiranandani Gardens. Breakfast and dinner included, CCTV at entry, warden on site.'),
    ('Budget PG in Kharghar Sector 12', 'Navi Mumbai', 'Kharghar', 7500, 'Triple Sharing', 'Semi-Furnished', 'Any', 220,
     ['Wi-Fi', 'In-house Mess', 'Washing Machine (Private/Common)', 'Power Backup'],
     'Ideal for students of nearby colleges. Bus stop at the gate, home-style veg food, study table for each bed.'),
    ('Co-living Room near Thane Station', 'Thane', 'Thane West', 9500, 'Double Sharing', 'Furnished', 'Any', 200,
     ['Wi-Fi', 'AC', 'Lift/Elevator', 'Security', 'Refrigerator'],
     'Modern co-living with a shared lounge and pantry. 10 minutes from Thane station, housekeeping three times a week.'),
    ('Girls PG near Vashi Station', 'Navi Mumbai', 'Vashi', 10000, 'Double Sharing', 'Furnished', 'Female', 170,
     ['Wi-Fi', 'In-house Mess', 'Security', 'Washing Machine (Private/Common)', 'Lift/Elevator'],
     'Safe building close to Inorbit Mall and Vashi station. Three meals a day, 10:30 pm entry time.'),
    ('Private Room PG on Baner Road', 'Pune', 'Baner', 13000, 'Single Room', 'Furnished', 'Any', 140,
     ['Wi-Fi', 'AC', 'Power Backup', 'Refrigerator', 'Security'],
     'Quiet private room for IT professionals on Baner Road. High-speed internet, power backup and daily cleaning.'),
    ('Boys PG near Dadar TT', 'Mumbai', 'Dadar East', 12000, 'Triple Sharing', 'Semi-Furnished', 'Male', 240,
     ['Wi-Fi', 'In-house Mess', 'Washing Machine (Private/Common)'],
     'Walking distance to Dadar station and markets. Lunch and dinner, cupboard and bed for each person.'),
    ('Premium PG in Hinjewadi Phase 1', 'Pune', 'Hinjewadi', 15000, 'Single Room', 'Furnished', 'Any', 160,
     ['Wi-Fi', 'AC', 'In-house Mess', 'Power Backup', 'Lift/Elevator', 'Security'],
     'Five minutes from the IT park. Attached washroom, AC room, buffet meals and a small gym on the terrace.'),
    ('Girls PG in Borivali West', 'Mumbai', 'Borivali West', 11500, 'Double Sharing', 'Furnished', 'Female', 190,
     ['Wi-Fi', 'AC', 'In-house Mess', 'Security', 'Refrigerator'],
     'Near Borivali station and the national park. Clean rooms, home-cooked food, lady warden.'),
    ('Student PG near Nerul Station', 'Navi Mumbai', 'Nerul', 8000, 'Triple Sharing', 'Semi-Furnished', 'Male', 230,
     ['Wi-Fi', 'In-house Mess', 'Power Backup'],
     'Popular with engineering students. 5 minutes to Nerul station, study area and veg mess.'),
]

RENTAL = [
    # title, city, area, rent, deposit, bhk, furnishing, sq_ft, broker, amenities, description
    ('Spacious 2 BHK in Andheri West', 'Mumbai', 'Andheri West', 52000, 150000, '2 BHK', 'Semi-Furnished', 850, False,
     ['Lift/Elevator', 'Security', 'Parking', 'Power Backup'],
     'Well-lit flat near Lokhandwala market with a balcony, modular kitchen and covered parking. Family preferred.'),
    ('1 RK near Ghatkopar Station', 'Mumbai', 'Ghatkopar East', 16000, 50000, '1 RK', 'Unfurnished', 300, False,
     ['Security', 'Lift/Elevator'],
     'Compact 1 RK, 5 minutes from Ghatkopar metro and railway. Ideal for a single working professional.'),
    ('Furnished 1 BHK in Powai', 'Mumbai', 'Powai', 38000, 120000, '1 BHK', 'Furnished', 560, False,
     ['AC', 'Wi-Fi', 'Lift/Elevator', 'Security', 'Gymnasium', 'Power Backup'],
     'Ready to move in. Sofa, bed, wardrobe, fridge and washing machine included. Lake view from the living room.'),
    ('2 BHK in Kharghar with Hill View', 'Navi Mumbai', 'Kharghar', 26000, 80000, '2 BHK', 'Semi-Furnished', 950, True,
     ['Lift/Elevator', 'Security', 'Parking', 'Gymnasium', 'Balcony'],
     'Gated society with a pool and gym, near Central Park. Two balconies with a view of the hills.'),
    ('3 BHK Family Flat in Thane', 'Thane', 'Ghodbunder Road', 42000, 150000, '3 BHK', 'Semi-Furnished', 1250, False,
     ['Lift/Elevator', 'Security', 'Parking', 'Power Backup', 'Gymnasium', 'Balcony'],
     'Large flat in a township with schools and a mall nearby. Two covered parking spots.'),
    ('1 BHK near Vashi Station', 'Navi Mumbai', 'Vashi', 22000, 70000, '1 BHK', 'Semi-Furnished', 520, False,
     ['Lift/Elevator', 'Security', 'Parking'],
     'Close to Vashi station and Inorbit Mall. Fitted kitchen and wardrobes, 24x7 water.'),
    ('2 BHK in Baner, Pune', 'Pune', 'Baner', 30000, 100000, '2 BHK', 'Furnished', 1000, True,
     ['AC', 'Wi-Fi', 'Lift/Elevator', 'Security', 'Parking', 'Power Backup'],
     'Fully furnished flat with ACs in both bedrooms. Walking distance to Baner high street.'),
    ('1 BHK in Chembur East', 'Mumbai', 'Chembur', 30000, 90000, '1 BHK', 'Unfurnished', 480, False,
     ['Lift/Elevator', 'Security'],
     'Quiet lane near Chembur station and the monorail. Newly painted, east-facing.'),
    ('2 BHK in Wakad near Highway', 'Pune', 'Wakad', 24000, 75000, '2 BHK', 'Semi-Furnished', 900, False,
     ['Lift/Elevator', 'Security', 'Parking', 'Gymnasium', 'Balcony'],
     'Easy access to Hinjewadi IT park. Society with a clubhouse, gym and children\'s play area.'),
    ('4 BHK Duplex in Bandra West', 'Mumbai', 'Bandra West', 185000, 600000, '4+ BHK', 'Furnished', 2200, True,
     ['AC', 'Wi-Fi', 'Lift/Elevator', 'Security', 'Parking', 'Power Backup', 'Gymnasium', 'Balcony'],
     'Sea-facing duplex near Carter Road with a private terrace, four bathrooms and two parking spots.'),
]

ROOMMATE_HAS_PLACE = [
    # name, age, gender, city, area, rent share, bhk, amenities, title, description
    ('Aarav Mehta', 26, 'Male', 'Mumbai', 'Andheri East', 15000, '2 BHK', ['Non-Smoker', 'Wi-Fi', 'AC', 'Lift/Elevator'],
     'Room available in 2 BHK, Andheri East', 'Software engineer, looking for a working professional to share my 2 BHK. Private room, shared kitchen.'),
    ('Priya Nair', 24, 'Female', 'Mumbai', 'Powai', 18000, '2 BHK', ['Non-Smoker', 'Vegetarian', 'Wi-Fi', 'AC'],
     'Female flatmate wanted in Powai', 'Analyst at a bank. Clean, quiet flat near Hiranandani. Looking for a female flatmate.'),
    ('Rohit Kulkarni', 28, 'Male', 'Pune', 'Hinjewadi', 11000, '3 BHK', ['Wi-Fi', 'Attached Bathroom', 'Reserved Parking'],
     'Room with attached bathroom, Hinjewadi', 'Room with attached bathroom in a 3 BHK. Two other flatmates, both in IT. Bike parking available.'),
    ('Sneha Iyer', 25, 'Female', 'Navi Mumbai', 'Vashi', 12000, '2 BHK', ['Non-Smoker', 'Vegetarian', 'Wi-Fi', 'Lift/Elevator'],
     'Shared 2 BHK near Vashi station', 'Looking for a vegetarian female flatmate. Furnished flat, 5 minutes from the station.'),
    ('Karan Shah', 27, 'Male', 'Mumbai', 'Bandra West', 22000, '2 BHK', ['Pet-Friendly', 'Wi-Fi', 'AC'],
     'Pet-friendly flat in Bandra', 'I have a friendly dog, so pet lovers only! Big living room, 10 minutes from Bandra station.'),
    ('Ananya Deshpande', 23, 'Female', 'Pune', 'Kothrud', 9000, '2 BHK', ['Non-Smoker', 'Vegetarian', 'Wi-Fi'],
     'Flatmate wanted in Kothrud', 'Masters student. Calm and tidy flat close to the college and the market.'),
    ('Vikram Joshi', 29, 'Male', 'Thane', 'Thane West', 12500, '2 BHK', ['Non-Smoker', 'Wi-Fi', 'Lift/Elevator', 'Reserved Parking'],
     'Room in a gated society, Thane', 'Room available in a society with a pool and gym. Car parking for the flatmate.'),
    ('Meera Pillai', 26, 'Female', 'Mumbai', 'Chembur', 14000, '2 BHK', ['Non-Smoker', 'Wi-Fi', 'AC', 'Attached Bathroom'],
     'Female flatmate wanted in Chembur', 'Doctor at a nearby hospital, often on night shifts. Room has an attached bathroom.'),
    ('Arjun Rao', 30, 'Male', 'Navi Mumbai', 'Kharghar', 10000, '3 BHK', ['Wi-Fi', 'Lift/Elevator', 'Reserved Parking'],
     'Spare room in Kharghar 3 BHK', 'Architect working from home most days. Large flat facing the hills, one room free.'),
    ('Isha Kapoor', 24, 'Female', 'Pune', 'Viman Nagar', 13000, '2 BHK', ['Non-Smoker', 'Wi-Fi', 'AC', 'Pet-Friendly'],
     'Room near Phoenix Mall, Viman Nagar', 'Designer with a cat. Bright flat, close to the airport and the mall.'),
]

ROOMMATE_LOOKING = [
    # name, age, gender, city, area, budget, amenities, title, description
    ('Rahul Verma', 24, 'Male', 'Mumbai', 'Andheri', 12000, ['Non-Smoker', 'Wi-Fi'],
     'Fresher looking for a shared flat in Andheri', 'Joining a company in Andheri next month. Looking for a room in a shared flat near the metro.'),
    ('Neha Gupta', 25, 'Female', 'Mumbai', 'Powai', 15000, ['Non-Smoker', 'Vegetarian', 'Wi-Fi'],
     'Looking for a female flatmate in Powai', 'Working in Powai, looking to share a 2 BHK with another working woman.'),
    ('Siddharth Patil', 27, 'Male', 'Pune', 'Hinjewadi', 10000, ['Wi-Fi', 'Reserved Parking'],
     'Need a room near Hinjewadi', 'Software developer moving from Nagpur. Need bike parking and good internet.'),
    ('Pooja Reddy', 23, 'Female', 'Navi Mumbai', 'Kharghar', 9000, ['Non-Smoker', 'Vegetarian'],
     'Student looking for a flat in Kharghar', 'MBA student, looking for a calm flat with other students near college.'),
    ('Aditya Singh', 26, 'Male', 'Thane', 'Thane West', 11000, ['Non-Smoker', 'Wi-Fi', 'Lift/Elevator'],
     'Looking for a flatmate in Thane', 'Want to rent a 2 BHK together and split costs. Prefer near the station.'),
    ('Kavya Menon', 24, 'Female', 'Mumbai', 'Bandra', 18000, ['Non-Smoker', 'Pet-Friendly', 'Wi-Fi'],
     'Looking for a pet-friendly flat in Bandra', 'Content writer with a small dog. Looking for a room in a pet-friendly flat.'),
    ('Manish Yadav', 28, 'Male', 'Navi Mumbai', 'Vashi', 10000, ['Wi-Fi', 'AC'],
     'Room needed near Vashi station', 'Bank employee, very regular routine. Need a room close to the station.'),
    ('Ritika Jain', 22, 'Female', 'Pune', 'Kothrud', 8000, ['Vegetarian', 'Non-Smoker'],
     'Vegetarian student looking for a flat in Kothrud', 'Final-year student, looking for vegetarian flatmates near Karve Road.'),
    ('Harsh Malhotra', 29, 'Male', 'Mumbai', 'Lower Parel', 20000, ['Wi-Fi', 'AC', 'Attached Bathroom'],
     'Looking for a room near Lower Parel', 'Consultant who travels on weekdays. Need a room with an attached bathroom.'),
    ('Tanvi Sawant', 26, 'Female', 'Mumbai', 'Dadar', 14000, ['Non-Smoker', 'Vegetarian', 'Wi-Fi'],
     'Female flatmate needed near Dadar', 'Teacher, looking for a female flatmate to share a flat in Dadar or Matunga.'),
]


def add_listings(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Property = apps.get_model('listings', 'Property')
    Amenity = apps.get_model('listings', 'Amenity')
    ListingImage = apps.get_model('listings', 'ListingImage')

    if User.objects.filter(username=SAMPLE_USERNAME).exists():
        return  # already added
    owner = User.objects.create(username=SAMPLE_USERNAME, first_name='SetMyStay', last_name='Samples',
                                is_active=False, password='!')  # '!' = can never sign in

    amenity_cache = {}

    def amenity(name):
        if name not in amenity_cache:
            obj = Amenity.objects.filter(name=name).first() or Amenity.objects.create(name=name)
            amenity_cache[name] = obj
        return amenity_cache[name]

    now = timezone.now()
    made = []

    def create(i, images, amenities, **fields):
        p = Property.objects.create(owner=owner, status='APPROVED', state='Maharashtra', **fields)
        p.amenities.set([amenity(a) for a in amenities])
        for url in images:
            ListingImage.objects.create(property=p, image_url=url, is_video=False)
        made.append(p.id)
        # spread "listed on" dates over the last two weeks
        Property.objects.filter(id=p.id).update(created_at=now - timedelta(hours=7 + i * 9))

    n = 0
    for i, (title, city, area, rent, room, furn, gender, sqft, amen, desc) in enumerate(PG):
        create(n, pick(BEDROOM, i, 2) + pick(BUILDING, i), amen,
               property_type='PG', title=title, description=desc, rent=rent, deposit=rent,
               city=city, area=area, address=f'{area}, {city}', bhk='', furnishing=furn, sq_ft=sqft,
               occupancy_type=room, gender_preference=gender, owner_name=OWNER, phone_primary=OFFICE_PHONE)
        n += 1
    for i, (title, city, area, rent, dep, bhk, furn, sqft, broker, amen, desc) in enumerate(RENTAL):
        create(n, pick(BUILDING, i + 2) + pick(LIVING, i, 2) + pick(BEDROOM, i + 3) + pick(KITCHEN, i), amen,
               property_type='RENTAL', title=title, description=desc, rent=rent, deposit=dep,
               city=city, area=area, address=f'{area}, {city}', bhk=bhk, furnishing=furn, sq_ft=sqft,
               is_broker=broker, owner_name=OWNER, phone_primary=OFFICE_PHONE)
        n += 1
    for i, (name, age, gender, city, area, rent, bhk, amen, title, desc) in enumerate(ROOMMATE_HAS_PLACE):
        create(n, pick(LIVING, i + 4, 2) + pick(BEDROOM, i + 1), amen,
               property_type='ROOMMATE', title=title, description=desc, rent=rent,
               city=city, area=area, address=f'{area}, {city}', bhk=bhk, furnishing='Furnished', sq_ft=650,
               gender_preference=gender, sharing_status='Living in', age=age,
               owner_name=name, phone_primary=OFFICE_PHONE)
        n += 1
    for i, (name, age, gender, city, area, budget, amen, title, desc) in enumerate(ROOMMATE_LOOKING):
        create(n, [avatar(name)], amen,
               property_type='ROOMMATE', title=title, description=desc, rent=budget,
               city=city, area=area, address=f'{area}, {city}', bhk='', furnishing='', sq_ft=None,
               gender_preference=gender, sharing_status='Moving soon', age=age,
               owner_name=name, phone_primary=OFFICE_PHONE)
        n += 1


def remove_listings(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.filter(username=SAMPLE_USERNAME).delete()  # listings and photos go with it


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0019_remove_test_unlock'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(add_listings, remove_listings),
    ]
