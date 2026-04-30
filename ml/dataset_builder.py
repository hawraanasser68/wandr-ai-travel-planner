import pandas as pd
import random

# --- EXISTING HIGH-QUALITY SAMPLE ROWS (DO NOT MODIFY) ---
existing_rows = [
    # Adventure
    {"destination_name": "Queenstown", "country": "New Zealand", "description": "Queenstown is renowned for its adrenaline-pumping activities, from bungee jumping to alpine hiking amid dramatic mountain scenery.", "key_activities": "bungee jumping, hiking, jet boating", "avg_cost_per_day": 180, "family_friendly": False, "label": "Adventure"},
    {"destination_name": "Torres del Paine", "country": "Chile", "description": "Torres del Paine National Park offers rugged trekking routes, glacier views, and untouched Patagonian wilderness for true adventurers.", "key_activities": "trekking, glacier hiking, wildlife watching", "avg_cost_per_day": 110, "family_friendly": False, "label": "Adventure"},
    {"destination_name": "Interlaken", "country": "Switzerland", "description": "Interlaken is a hub for outdoor sports, including paragliding, canyoning, and mountain biking in the Swiss Alps.", "key_activities": "paragliding, canyoning, mountain biking", "avg_cost_per_day": 160, "family_friendly": False, "label": "Adventure"},
    # Relaxation
    {"destination_name": "Bora Bora", "country": "French Polynesia", "description": "Bora Bora’s turquoise lagoons and overwater bungalows create a serene escape perfect for unwinding and spa indulgence.", "key_activities": "spa, beach lounging, snorkeling", "avg_cost_per_day": 400, "family_friendly": True, "label": "Relaxation"},
    {"destination_name": "Ubud", "country": "Indonesia", "description": "Ubud is a tranquil retreat surrounded by rice terraces, yoga studios, and wellness resorts ideal for relaxation.", "key_activities": "yoga, spa, meditation", "avg_cost_per_day": 90, "family_friendly": True, "label": "Relaxation"},
    {"destination_name": "Seychelles", "country": "Seychelles", "description": "The Seychelles islands offer quiet beaches, gentle waves, and luxury resorts for a peaceful, restorative holiday.", "key_activities": "beach, spa, sailing", "avg_cost_per_day": 350, "family_friendly": True, "label": "Relaxation"},
    # Culture
    {"destination_name": "Kyoto", "country": "Japan", "description": "Kyoto is steeped in tradition, with centuries-old temples, vibrant festivals, and exquisite gardens reflecting Japanese heritage.", "key_activities": "temple visits, tea ceremonies, festivals", "avg_cost_per_day": 130, "family_friendly": True, "label": "Culture"},
    {"destination_name": "Florence", "country": "Italy", "description": "Florence is the heart of the Renaissance, boasting world-class museums, historic cathedrals, and iconic art galleries.", "key_activities": "museums, art galleries, historic tours", "avg_cost_per_day": 150, "family_friendly": True, "label": "Culture"},
    {"destination_name": "Marrakech", "country": "Morocco", "description": "Marrakech enchants with its bustling souks, ancient palaces, and rich blend of Berber and Arab culture.", "key_activities": "souks, palace tours, traditional cuisine", "avg_cost_per_day": 90, "family_friendly": True, "label": "Culture"},
    # Budget
    {"destination_name": "Hanoi", "country": "Vietnam", "description": "Hanoi is a lively city where travelers enjoy affordable street food, bustling markets, and budget hostels.", "key_activities": "street food, markets, city tours", "avg_cost_per_day": 35, "family_friendly": True, "label": "Budget"},
    {"destination_name": "Sofia", "country": "Bulgaria", "description": "Sofia offers historic sites, vibrant nightlife, and low-cost living, making it ideal for budget-conscious explorers.", "key_activities": "historic sites, nightlife, local cuisine", "avg_cost_per_day": 40, "family_friendly": True, "label": "Budget"},
    {"destination_name": "Cusco", "country": "Peru", "description": "Cusco is a gateway to Machu Picchu, with affordable guesthouses and a backpacker-friendly vibe.", "key_activities": "backpacking, local markets, city walks", "avg_cost_per_day": 30, "family_friendly": True, "label": "Budget"},
    # Luxury
    {"destination_name": "Dubai", "country": "United Arab Emirates", "description": "Dubai dazzles with luxury shopping, five-star hotels, and world-class fine dining in a futuristic cityscape.", "key_activities": "luxury shopping, fine dining, spa", "avg_cost_per_day": 500, "family_friendly": True, "label": "Luxury"},
    {"destination_name": "St. Moritz", "country": "Switzerland", "description": "St. Moritz is a glamorous alpine resort known for upscale skiing, designer boutiques, and gourmet restaurants.", "key_activities": "skiing, designer shopping, gourmet dining", "avg_cost_per_day": 600, "family_friendly": True, "label": "Luxury"},
    {"destination_name": "Maldives", "country": "Maldives", "description": "The Maldives features exclusive overwater villas, private beaches, and premium spa experiences for discerning travelers.", "key_activities": "private beach, spa, snorkeling", "avg_cost_per_day": 700, "family_friendly": True, "label": "Luxury"},
    # Family
    {"destination_name": "Orlando", "country": "USA", "description": "Orlando is home to world-famous theme parks, water parks, and family-friendly resorts designed for children of all ages.", "key_activities": "theme parks, water parks, family resorts", "avg_cost_per_day": 250, "family_friendly": True, "label": "Family"},
    {"destination_name": "Gold Coast", "country": "Australia", "description": "Gold Coast features sandy beaches, amusement parks, and wildlife sanctuaries perfect for families seeking fun and adventure.", "key_activities": "beaches, amusement parks, wildlife", "avg_cost_per_day": 180, "family_friendly": True, "label": "Family"},
    {"destination_name": "Copenhagen", "country": "Denmark", "description": "Copenhagen offers safe streets, interactive museums, and parks ideal for children and families.", "key_activities": "museums, parks, cycling", "avg_cost_per_day": 200, "family_friendly": True, "label": "Family"},
]

# --- CLASS LABELS ---
labels = ["Adventure", "Relaxation", "Culture", "Budget", "Luxury", "Family"]

# --- DESTINATION POOLS FOR EXPANSION (examples, can be extended) ---
destination_pools = {
    "Adventure": [
        ("Banff", "Canada", "Banff National Park is a haven for hikers and climbers, surrounded by turquoise lakes and rugged peaks.", "hiking, climbing, canoeing", 140, False),
        ("Moab", "USA", "Moab is famous for its red rock landscapes, mountain biking trails, and canyoneering adventures.", "mountain biking, canyoneering, rock climbing", 120, False),
        ("Chamonix", "France", "Chamonix offers world-class skiing, mountaineering, and glacier trekking in the French Alps.", "skiing, mountaineering, glacier trekking", 210, False),
        ("Cusco", "Peru", "Cusco is a gateway to the Inca Trail, attracting trekkers and adventure seekers from around the world.", "trekking, hiking, mountain biking", 90, False),
        ("Cape Town", "South Africa", "Cape Town is a paradise for surfers, hikers, and nature lovers with Table Mountain as a backdrop.", "surfing, hiking, nature walks", 110, False),
        ("Whistler", "Canada", "Whistler is a top destination for skiing, snowboarding, and mountain biking in North America.", "skiing, snowboarding, mountain biking", 200, False),
        ("Patagonia", "Argentina", "Patagonia offers dramatic landscapes, glacier hikes, and challenging trekking routes for thrill-seekers.", "trekking, glacier hiking, wildlife watching", 120, False),
        ("Zermatt", "Switzerland", "Zermatt is famed for its alpine skiing, mountaineering, and breathtaking views of the Matterhorn.", "alpine skiing, mountaineering, hiking", 220, False),
        ("Rotorua", "New Zealand", "Rotorua is known for its geothermal parks, mountain biking, and Maori adventure experiences.", "mountain biking, geothermal parks, adventure tours", 130, False),
        ("Yosemite", "USA", "Yosemite National Park is a mecca for rock climbers, hikers, and nature photographers.", "rock climbing, hiking, photography", 100, False),
        ("Aoraki/Mount Cook", "New Zealand", "Aoraki/Mount Cook offers glacier walks, alpine climbing, and stargazing in pristine wilderness.", "glacier walks, alpine climbing, stargazing", 150, False),
        ("Lofoten Islands", "Norway", "Lofoten Islands are perfect for kayaking, hiking, and arctic surfing in dramatic northern scenery.", "kayaking, hiking, arctic surfing", 160, False),
        ("Lake District", "UK", "The Lake District is known for scenic hiking trails, boating, and outdoor adventures in rolling hills.", "hiking, boating, outdoor adventures", 110, False),
        ("Sagarmatha National Park", "Nepal", "Sagarmatha National Park is home to Everest Base Camp treks and Himalayan expeditions.", "trekking, expeditions, mountain climbing", 90, False),
        ("Blue Mountains", "Australia", "The Blue Mountains offer bushwalking, canyoning, and abseiling in dramatic sandstone landscapes.", "bushwalking, canyoning, abseiling", 120, False),
        ("Queen Charlotte Track", "New Zealand", "Queen Charlotte Track is a scenic route for hiking and mountain biking along New Zealand’s coast.", "hiking, mountain biking, kayaking", 140, False),
        ("Sapa", "Vietnam", "Sapa is known for terraced rice fields, trekking routes, and ethnic minority villages.", "trekking, village visits, hiking", 60, False),
        ("Drakensberg", "South Africa", "The Drakensberg mountains are ideal for hiking, rock climbing, and horseback riding.", "hiking, rock climbing, horseback riding", 100, False),
        ("Valle de Cocora", "Colombia", "Valle de Cocora features cloud forests, tall wax palms, and scenic trekking trails.", "trekking, horseback riding, nature walks", 80, False),
    ],
    "Relaxation": [
        ("Malaga", "Spain", "Malaga offers sunny beaches, palm-lined promenades, and a laid-back Mediterranean vibe.", "beach, promenade walks, spa", 120, True),
        ("Phuket", "Thailand", "Phuket is famous for its white sand beaches, luxury spas, and tranquil island resorts.", "beach, spa, island tours", 140, True),
        ("Maui", "USA", "Maui is a Hawaiian paradise with lush scenery, gentle waves, and world-class wellness retreats.", "beach, wellness retreats, snorkeling", 250, True),
        ("Goa", "India", "Goa is known for its relaxed beaches, yoga retreats, and affordable seaside resorts.", "beach, yoga, relaxation", 70, True),
        ("Tahiti", "French Polynesia", "Tahiti’s calm lagoons, overwater bungalows, and spa treatments make it a top relaxation spot.", "spa, lagoon swimming, beach", 300, True),
        ("Nice", "France", "Nice features pebble beaches, seaside cafes, and a relaxed Riviera atmosphere.", "beach, cafes, promenade", 180, True),
        ("Langkawi", "Malaysia", "Langkawi is an island escape with quiet beaches, mangrove tours, and luxury resorts.", "beach, mangrove tours, spa", 130, True),
        ("Koh Samui", "Thailand", "Koh Samui is a tropical island with palm-fringed beaches, yoga studios, and wellness centers.", "beach, yoga, wellness", 110, True),
        ("Tulum", "Mexico", "Tulum offers eco-chic resorts, white sand beaches, and a peaceful Caribbean setting.", "beach, eco resorts, spa", 160, True),
        ("Santorini", "Greece", "Santorini is famous for its sunsets, cliffside pools, and relaxing Mediterranean ambiance.", "sunset viewing, spa, beach", 200, True),
        ("Bali", "Indonesia", "Bali’s serene rice terraces, spa retreats, and gentle beaches attract those seeking relaxation.", "spa, rice terraces, beach", 100, True),
        ("Port Douglas", "Australia", "Port Douglas is a quiet gateway to the Great Barrier Reef, with palm-lined beaches and luxury spas.", "beach, spa, reef tours", 180, True),
        ("Lake Como", "Italy", "Lake Como is a tranquil retreat with lakeside villas, gardens, and scenic boat rides.", "boat rides, gardens, spa", 220, True),
        ("Hoi An", "Vietnam", "Hoi An is a riverside town with lantern-lit evenings, calm beaches, and boutique resorts.", "beach, lantern walks, spa", 80, True),
        ("Mauritius", "Mauritius", "Mauritius offers turquoise lagoons, coral reefs, and luxury beach resorts for relaxation.", "beach, snorkeling, spa", 210, True),
        ("Palm Springs", "USA", "Palm Springs is known for its desert spas, golf courses, and mid-century modern resorts.", "spa, golf, pool lounging", 170, True),
        ("Fiji", "Fiji", "Fiji’s islands are perfect for unwinding with soft sand beaches, gentle surf, and wellness retreats.", "beach, wellness, snorkeling", 190, True),
        ("Amalfi Coast", "Italy", "The Amalfi Coast features cliffside hotels, lemon groves, and a relaxed Mediterranean pace.", "beach, scenic drives, spa", 230, True),
    ],
    "Culture": [
        ("Paris", "France", "Paris is a cultural capital with world-renowned museums, historic landmarks, and vibrant arts.", "museums, art galleries, historic sites", 180, True),
        ("Istanbul", "Turkey", "Istanbul bridges Europe and Asia, offering a rich tapestry of mosques, bazaars, and centuries-old palaces.", "mosque visits, bazaars, palace tours", 100, True),
        ("Prague", "Czech Republic", "Prague’s cobbled streets, Gothic cathedrals, and historic squares make it a cultural gem.", "cathedrals, historic squares, museums", 90, True),
        ("Beijing", "China", "Beijing is home to the Forbidden City, ancient temples, and a deep imperial history.", "palace tours, temples, museums", 120, True),
        ("Cusco", "Peru", "Cusco is a gateway to Machu Picchu, with Incan ruins and colonial architecture.", "Incan ruins, museums, city walks", 70, True),
        ("Cairo", "Egypt", "Cairo’s ancient pyramids, bustling bazaars, and museums showcase millennia of history.", "pyramids, museums, bazaars", 80, True),
        ("Vienna", "Austria", "Vienna is famed for its imperial palaces, classical music, and grand museums.", "palaces, music halls, museums", 160, True),
        ("Mexico City", "Mexico", "Mexico City boasts Aztec ruins, colonial cathedrals, and a thriving arts scene.", "ruins, cathedrals, art museums", 70, True),
        ("St. Petersburg", "Russia", "St. Petersburg is known for its grand palaces, ballet, and world-class museums.", "palaces, ballet, museums", 140, True),
        ("Athens", "Greece", "Athens is the cradle of Western civilization, with ancient ruins and archaeological museums.", "ruins, museums, historic tours", 110, True),
        ("Fez", "Morocco", "Fez is a medieval city with labyrinthine souks, madrasas, and centuries-old craftsmanship.", "souks, madrasas, museums", 60, True),
        ("Petra", "Jordan", "Petra’s rock-cut architecture and archaeological wonders attract history lovers worldwide.", "archaeology, hiking, museums", 100, True),
        ("Lviv", "Ukraine", "Lviv is a UNESCO-listed city with baroque churches, coffeehouses, and literary history.", "churches, museums, coffeehouses", 50, True),
        ("Granada", "Spain", "Granada is home to the Alhambra, flamenco culture, and Moorish architecture.", "Alhambra, flamenco, architecture", 90, True),
        ("Salzburg", "Austria", "Salzburg is Mozart’s birthplace, with baroque palaces and classical music festivals.", "music festivals, palaces, museums", 130, True),
        ("Cartagena", "Colombia", "Cartagena’s walled city, colonial plazas, and Caribbean history make it a cultural treasure.", "historic plazas, museums, walking tours", 80, True),
        ("Chiang Mai", "Thailand", "Chiang Mai is known for its ancient temples, night markets, and traditional festivals.", "temples, markets, festivals", 60, True),
        ("Jerusalem", "Israel", "Jerusalem is a crossroads of religions, with sacred sites and centuries of history.", "sacred sites, museums, old city tours", 120, True),
        ("New York", "USA", "New York City offers world-class museums, Broadway shows, and iconic landmarks.", "museums, Broadway, landmarks", 250, True),
    ],
    "Budget": [
        ("Bangkok", "Thailand", "Bangkok is a backpacker’s paradise with cheap eats, lively hostels, and bustling street markets.", "street food, hostels, markets", 30, True),
        ("La Paz", "Bolivia", "La Paz offers unique culture, colorful markets, and low-cost travel experiences in the Andes.", "markets, walking tours, cable car rides", 25, True),
        ("Krakow", "Poland", "Krakow is a budget-friendly city with historic squares, affordable hostels, and hearty cuisine.", "historic squares, hostels, local cuisine", 35, True),
        ("Budapest", "Hungary", "Budapest features thermal baths, ruin pubs, and cheap eats for budget travelers.", "thermal baths, ruin pubs, cheap eats", 40, True),
        ("Belgrade", "Serbia", "Belgrade is known for its affordable nightlife, riverside cafes, and historic fortresses.", "nightlife, cafes, fortresses", 30, True),
        ("Kathmandu", "Nepal", "Kathmandu is a budget hub for trekkers, with cheap guesthouses and vibrant bazaars.", "trekking, bazaars, guesthouses", 25, True),
        ("Marrakesh", "Morocco", "Marrakesh offers affordable riads, street food, and lively souks for budget travelers.", "riads, street food, souks", 30, True),
        ("Manila", "Philippines", "Manila is a bustling city with budget hotels, street eats, and lively markets.", "street eats, markets, city tours", 25, True),
        ("Tbilisi", "Georgia", "Tbilisi is a rising budget destination with cheap wine, hostels, and old town charm.", "wine, hostels, old town", 30, True),
        ("Lima", "Peru", "Lima offers affordable ceviche, hostels, and Pacific coast views for budget travelers.", "ceviche, hostels, coast views", 35, True),
        ("Santiago", "Chile", "Santiago is a South American capital with budget eats, metro access, and lively plazas.", "budget eats, metro, plazas", 40, True),
        ("Zagreb", "Croatia", "Zagreb is a walkable city with cheap cafes, museums, and hostels.", "cafes, museums, hostels", 35, True),
        ("Valencia", "Spain", "Valencia offers affordable beaches, paella, and lively festivals for budget travelers.", "beaches, paella, festivals", 45, True),
        ("Sihanoukville", "Cambodia", "Sihanoukville is a beach town with budget bungalows, street food, and backpacker bars.", "bungalows, street food, bars", 20, True),
        ("Pokhara", "Nepal", "Pokhara is a lakeside city with cheap guesthouses, trekking, and paragliding.", "guesthouses, trekking, paragliding", 25, True),
        ("Sarajevo", "Bosnia & Herzegovina", "Sarajevo is a budget-friendly city with history, cafes, and affordable hostels.", "history, cafes, hostels", 30, True),

        # Additional budget destinations
        ("Hanoi Old Quarter", "Vietnam", "The Old Quarter in Hanoi is packed with cheap hostels, street food, and lively markets.", "hostels, street food, markets", 20, True),
        ("Sapa", "Vietnam", "Sapa offers affordable trekking, homestays, and local markets in the mountains.", "trekking, homestays, markets", 25, True),
        ("Chiang Mai", "Thailand", "Chiang Mai is a budget-friendly city with night markets, temples, and cheap guesthouses.", "night markets, temples, guesthouses", 30, True),
        ("Goa", "India", "Goa is a favorite for budget travelers with beach huts, cheap eats, and lively shacks.", "beach huts, cheap eats, shacks", 25, True),
        ("Sofia City", "Bulgaria", "Sofia offers affordable museums, hostels, and local cuisine for budget travelers.", "museums, hostels, cuisine", 20, True),
        ("Cairo Downtown", "Egypt", "Downtown Cairo has budget hotels, street food, and historic sites.", "budget hotels, street food, historic sites", 20, True),
        ("Cusco Backpacker", "Peru", "Cusco's backpacker district is filled with cheap hostels and lively bars.", "hostels, bars, markets", 20, True),
        ("Mexico City Centro", "Mexico", "Centro is the heart of Mexico City with budget eats, museums, and hostels.", "budget eats, museums, hostels", 25, True),
        ("Bucharest", "Romania", "Bucharest is a budget European capital with cheap hostels, parks, and nightlife.", "hostels, parks, nightlife", 20, True),
        ("Belgrade Skadarlija", "Serbia", "Skadarlija is a bohemian quarter with affordable cafes, hostels, and live music.", "cafes, hostels, live music", 20, True),
        ("Manila Intramuros", "Philippines", "Intramuros offers budget stays, street eats, and colonial history.", "budget stays, street eats, history", 20, True),
        ("Kathmandu Thamel", "Nepal", "Thamel is a budget hub for trekkers with cheap guesthouses and lively streets.", "guesthouses, trekking, nightlife", 20, True),
        ("Tirana", "Albania", "Tirana is an affordable Balkan capital with hostels, cafes, and local food.", "hostels, cafes, local food", 20, True),
        ("La Paz Centro", "Bolivia", "Centro La Paz has budget hotels, markets, and street food.", "hotels, markets, street food", 20, True),
        ("Siem Reap", "Cambodia", "Siem Reap is a backpacker base for Angkor Wat with cheap hostels and night markets.", "hostels, night markets, temples", 20, True),
        ("Huaraz", "Peru", "Huaraz is a budget trekking town with hostels and mountain views.", "trekking, hostels, mountain views", 20, True),
        ("Lviv", "Ukraine", "Lviv is a cheap city with coffeehouses, hostels, and historic squares.", "coffeehouses, hostels, squares", 20, True),
        ("Marrakech Medina", "Morocco", "The Medina offers budget riads, souks, and street food.", "riads, souks, street food", 20, True),
        ("Valparaiso", "Chile", "Valparaiso is a colorful port city with budget hostels and street art.", "hostels, street art, port", 20, True),
    ],
    "Luxury": [
        ("Aspen", "USA", "Aspen is a luxury ski resort with designer boutiques, gourmet dining, and exclusive chalets.", "skiing, designer shopping, gourmet dining", 700, True),
        ("Monaco", "Monaco", "Monaco is synonymous with luxury casinos, superyachts, and high-end shopping.", "casinos, yachting, luxury shopping", 900, True),
        ("St. Barts", "France", "St. Barts is a Caribbean island with upscale villas, private beaches, and celebrity sightings.", "private beaches, villas, fine dining", 800, True),
        ("Seychelles", "Seychelles", "Seychelles offers luxury resorts, private islands, and world-class spa treatments.", "luxury resorts, private islands, spa", 650, True),
        ("Lake Como", "Italy", "Lake Como is a tranquil retreat with lakeside villas, gardens, and scenic boat rides.", "boat rides, gardens, spa", 220, True),
        ("Santorini", "Greece", "Santorini is famous for its sunsets, cliffside pools, and relaxing Mediterranean ambiance.", "sunset viewing, spa, beach", 200, True),
        ("Maui", "USA", "Maui is a Hawaiian paradise with lush scenery, gentle waves, and world-class wellness retreats.", "beach, wellness retreats, snorkeling", 250, True),
        ("Portofino", "Italy", "Portofino is a picturesque harbor town with luxury yachts, designer boutiques, and gourmet seafood.", "yachting, designer shopping, gourmet seafood", 600, True),
        ("Courchevel", "France", "Courchevel is a premier ski resort with Michelin-starred restaurants and luxury chalets.", "skiing, fine dining, luxury chalets", 750, True),
        ("Abu Dhabi", "United Arab Emirates", "Abu Dhabi boasts opulent hotels, grand mosques, and luxury shopping malls.", "luxury hotels, mosques, shopping", 550, True),
        ("Cannes", "France", "Cannes is known for its film festival, luxury hotels, and private beaches.", "film festival, luxury hotels, beaches", 500, True),
        ("Venice", "Italy", "Venice offers luxury canal-side hotels, gourmet dining, and private gondola rides.", "gondola rides, gourmet dining, luxury hotels", 450, True),
        ("Tokyo", "Japan", "Tokyo’s luxury hotels, Michelin-starred restaurants, and designer shopping attract high-end travelers.", "luxury hotels, fine dining, shopping", 500, True),
        ("London", "UK", "London features five-star hotels, exclusive clubs, and luxury shopping districts.", "luxury hotels, clubs, shopping", 550, True),
        ("Zurich", "Switzerland", "Zurich is a financial hub with luxury boutiques, gourmet chocolate, and lakefront hotels.", "luxury boutiques, chocolate, hotels", 600, True),
        ("Los Cabos", "Mexico", "Los Cabos is a luxury beach destination with upscale resorts, golf, and private villas.", "resorts, golf, private villas", 650, True),

        # Additional luxury destinations
        ("Dubai Marina", "United Arab Emirates", "Dubai Marina is lined with luxury yachts, high-end restaurants, and exclusive beach clubs.", "yachting, fine dining, beach clubs", 700, True),
        ("Gstaad", "Switzerland", "Gstaad is a glamorous mountain village with luxury chalets, designer boutiques, and gourmet cuisine.", "luxury chalets, designer shopping, gourmet cuisine", 800, True),
        ("Beverly Hills", "USA", "Beverly Hills is famous for its upscale hotels, celebrity sightings, and luxury shopping on Rodeo Drive.", "luxury hotels, shopping, celebrity tours", 900, True),
        ("Mykonos", "Greece", "Mykonos is a chic island with exclusive beach clubs, luxury villas, and vibrant nightlife.", "beach clubs, luxury villas, nightlife", 650, True),
        ("Monte Carlo", "Monaco", "Monte Carlo is renowned for its grand casino, luxury hotels, and Formula 1 glamour.", "casino, luxury hotels, Formula 1", 950, True),
        ("St. Tropez", "France", "St. Tropez is a Mediterranean hotspot for luxury yachts, designer boutiques, and private beaches.", "yachting, designer shopping, private beaches", 850, True),
        ("Marrakech Palmeraie", "Morocco", "The Palmeraie in Marrakech offers luxury resorts, golf courses, and spa retreats.", "luxury resorts, golf, spa", 700, True),
        ("Sanya", "China", "Sanya is known as the 'Hawaii of China' with luxury beachfront resorts and tropical scenery.", "beach resorts, spa, golf", 600, True),
        ("Queenstown Luxury", "New Zealand", "Queenstown offers high-end lodges, helicopter tours, and exclusive adventure experiences.", "luxury lodges, helicopter tours, adventure", 750, True),
        ("Capri", "Italy", "Capri is an exclusive island with luxury hotels, designer shopping, and gourmet seafood.", "luxury hotels, shopping, gourmet seafood", 800, True),
        ("The Hamptons", "USA", "The Hamptons are a summer retreat for the elite, with private beaches and luxury estates.", "private beaches, luxury estates, fine dining", 900, True),
        ("Lake Geneva", "Switzerland", "Lake Geneva features luxury lakeside hotels, spas, and gourmet restaurants.", "lakeside hotels, spa, gourmet dining", 700, True),
        ("Doha", "Qatar", "Doha offers opulent hotels, luxury malls, and fine dining along the Corniche.", "luxury hotels, malls, fine dining", 650, True),
        ("Ibiza", "Spain", "Ibiza is known for its luxury beach clubs, exclusive parties, and upscale resorts.", "beach clubs, parties, resorts", 700, True),
        ("St. Lucia", "Saint Lucia", "St. Lucia offers luxury resorts, private beaches, and spa retreats in the Caribbean.", "luxury resorts, private beaches, spa", 750, True),
        ("Aspen Highlands", "USA", "Aspen Highlands is a premier ski destination with luxury lodges and gourmet dining.", "skiing, luxury lodges, gourmet dining", 800, True),
    ],
    "Family": [
        ("Anaheim", "USA", "Anaheim is home to Disneyland Resort, offering magical experiences for children and families.", "theme parks, Disneyland, family resorts", 260, True),
        ("Singapore", "Singapore", "Singapore boasts world-class zoos, theme parks, and interactive science centers for families.", "zoos, theme parks, science centers", 220, True),
        ("San Diego", "USA", "San Diego is known for its zoo, SeaWorld, and family-friendly beaches.", "zoo, SeaWorld, beaches", 210, True),
        ("Tokyo", "Japan", "Tokyo offers Disneyland, kid-friendly museums, and amusement parks for families.", "Disneyland, museums, amusement parks", 230, True),
        ("Toronto", "Canada", "Toronto features the Ontario Science Centre, zoos, and amusement parks for children.", "science centre, zoos, amusement parks", 180, True),
        ("Hong Kong", "Hong Kong", "Hong Kong Disneyland and Ocean Park make it a top family destination in Asia.", "Disneyland, Ocean Park, family attractions", 210, True),
        ("Paris", "France", "Paris offers Disneyland Paris, city parks, and interactive museums for families.", "Disneyland, parks, museums", 240, True),
        ("Dubai", "United Arab Emirates", "Dubai has indoor ski slopes, water parks, and theme parks for family fun.", "indoor skiing, water parks, theme parks", 300, True),
        ("London", "UK", "London features kid-friendly museums, zoos, and the Harry Potter Studio Tour.", "museums, zoos, Harry Potter Tour", 260, True),
        ("Munich", "Germany", "Munich offers the Deutsches Museum, city parks, and LEGOLAND for families.", "museums, parks, LEGOLAND", 170, True),
        ("Sydney", "Australia", "Sydney has Taronga Zoo, aquariums, and family beaches.", "zoo, aquariums, beaches", 200, True),
        ("Barcelona", "Spain", "Barcelona features the Tibidabo amusement park, city beaches, and science museums.", "amusement park, beaches, museums", 190, True),
        ("Stockholm", "Sweden", "Stockholm offers Junibacken, Skansen open-air museum, and family-friendly parks.", "Junibacken, Skansen, parks", 180, True),
        ("Los Angeles", "USA", "Los Angeles is home to Universal Studios, kid-friendly museums, and beaches.", "Universal Studios, museums, beaches", 270, True),
        ("Vienna", "Austria", "Vienna has the Prater amusement park, zoos, and children’s museums.", "Prater, zoos, museums", 210, True),

        # Additional family destinations
        ("Orlando", "USA", "Orlando is home to world-famous theme parks, water parks, and family-friendly resorts designed for children of all ages.", "theme parks, water parks, family resorts", 250, True),
        ("Billund", "Denmark", "Billund is the birthplace of LEGO and home to LEGOLAND, a paradise for kids.", "LEGOLAND, theme parks, family attractions", 180, True),
        ("Gold Coast", "Australia", "Gold Coast features sandy beaches, amusement parks, and wildlife sanctuaries perfect for families seeking fun and adventure.", "beaches, amusement parks, wildlife", 180, True),
        ("Sentosa", "Singapore", "Sentosa Island offers Universal Studios, water parks, and kid-friendly beaches.", "Universal Studios, water parks, beaches", 220, True),
        ("Orlando Water Parks", "USA", "Orlando's water parks provide endless fun for children and families.", "water parks, family resorts, theme parks", 230, True),
        ("Niagara Falls", "Canada", "Niagara Falls has family attractions, boat tours, and interactive museums.", "boat tours, museums, family attractions", 210, True),
        ("Dubai Parks", "United Arab Emirates", "Dubai Parks and Resorts is a mega theme park complex for families.", "theme parks, water parks, resorts", 320, True),
        ("Atlanta", "USA", "Atlanta offers the Georgia Aquarium, zoo, and interactive science museums for families.", "aquarium, zoo, science museums", 180, True),
        ("Orlando Studios", "USA", "Universal Studios Orlando is a top destination for family entertainment.", "Universal Studios, theme parks, family resorts", 260, True),
        ("Madrid", "Spain", "Madrid has Parque de Atracciones, zoo, and family-friendly museums.", "amusement park, zoo, museums", 200, True),
        ("Brisbane", "Australia", "Brisbane offers Lone Pine Koala Sanctuary, parks, and family attractions.", "koala sanctuary, parks, family attractions", 170, True),
        ("Osaka", "Japan", "Osaka is home to Universal Studios Japan and kid-friendly museums.", "Universal Studios, museums, parks", 210, True),
        ("Copenhagen Tivoli", "Denmark", "Tivoli Gardens in Copenhagen is one of the world's oldest amusement parks.", "Tivoli Gardens, amusement park, family attractions", 190, True),
        ("Hershey", "USA", "Hersheypark is a chocolate-themed amusement park for families.", "Hersheypark, amusement park, family attractions", 160, True),
        ("Orlando Disney", "USA", "Walt Disney World Resort in Orlando is the ultimate family vacation spot.", "Disney World, theme parks, family resorts", 300, True),
        ("Berlin", "Germany", "Berlin offers the Berlin Zoo, Legoland Discovery Centre, and family museums.", "zoo, Legoland, museums", 180, True),
        ("Vancouver", "Canada", "Vancouver has the Science World, aquarium, and Stanley Park for families.", "Science World, aquarium, Stanley Park", 200, True),
        ("Rome", "Italy", "Rome features Explora Children's Museum, Bioparco Zoo, and family-friendly parks.", "children's museum, zoo, parks", 190, True),
        ("Lisbon", "Portugal", "Lisbon offers Oceanário, kid-friendly trams, and interactive museums.", "Oceanário, trams, museums", 170, True),
        ("Seoul", "South Korea", "Seoul has Lotte World, Seoul Land, and family-friendly palaces.", "Lotte World, Seoul Land, palaces", 210, True),
    ],
}

# --- EXPAND DATASET ---
def expand_dataset(existing_rows, destination_pools, labels, min_per_class=20, max_total=150):
    # Count existing per class
    class_counts = {label: 0 for label in labels}
    for row in existing_rows:
        class_counts[row["label"]] += 1
    # Add new rows
    new_rows = []
    for label in labels:
        pool = destination_pools[label]
        random.shuffle(pool)
        needed = max(min_per_class - class_counts[label], 0)
        for entry in pool:
            if needed <= 0:
                break
            # Avoid duplicates by name+country
            if any((row["destination_name"], row["country"]) == (entry[0], entry[1]) for row in existing_rows + new_rows):
                continue
            new_rows.append({
                "destination_name": entry[0],
                "country": entry[1],
                "description": entry[2],
                "key_activities": entry[3],
                "avg_cost_per_day": entry[4],
                "family_friendly": entry[5],
                "label": label
            })
            needed -= 1
    # Combine and shuffle
    all_rows = existing_rows + new_rows
    random.shuffle(all_rows)
    # Truncate if over max_total
    if len(all_rows) > max_total:
        all_rows = all_rows[:max_total]
    return all_rows

if __name__ == "__main__":
    # Expand dataset to 200 rows, balanced
    all_rows = expand_dataset(existing_rows, destination_pools, labels, min_per_class=33, max_total=200)
    df = pd.DataFrame(all_rows)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # Shuffle
    df.to_csv("travel_dataset.csv", index=False)
    # Print class distribution
    print("Class distribution:")
    print(df["label"].value_counts())
    print(f"Total rows: {len(df)}")
