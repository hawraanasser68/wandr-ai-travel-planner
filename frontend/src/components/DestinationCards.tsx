/** Extracts bolded destination names from markdown and shows image cards. */

const IMAGES: Record<string, string> = {
  bali: "https://upload.wikimedia.org/wikipedia/commons/thumb/6/60/Pura_Ulun_Danu_Bratan%2C_Bali.jpg/480px-Pura_Ulun_Danu_Bratan%2C_Bali.jpg",
  kyoto: "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Fushimi_Inari_Taisha.jpg/480px-Fushimi_Inari_Taisha.jpg",
  tokyo: "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Skyscrapers_of_Shinjuku_2009_January.jpg/480px-Skyscrapers_of_Shinjuku_2009_January.jpg",
  santorini: "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Oia_02.jpg/480px-Oia_02.jpg",
  dubai: "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Burj_Khalifa_from_Burj_Al_Arab.jpg/480px-Burj_Khalifa_from_Burj_Al_Arab.jpg",
  maldives: "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Maldives_beach.jpg/480px-Maldives_beach.jpg",
  bangkok: "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Wat_Arun_in_Bangkok.jpg/480px-Wat_Arun_in_Bangkok.jpg",
  paris: "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Tour_Eiffel_Wikimedia_Commons.jpg/480px-Tour_Eiffel_Wikimedia_Commons.jpg",
  florence: "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Ponte_Vecchio_Florence.jpg/480px-Ponte_Vecchio_Florence.jpg",
  lisbon: "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Praça_do_Comércio%2C_Lisbon_-_World_Images.jpg/480px-Praça_do_Comércio%2C_Lisbon_-_World_Images.jpg",
  queenstown: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Queenstown_New_Zealand_Rees_Street_2.jpg/480px-Queenstown_New_Zealand_Rees_Street_2.jpg",
  patagonia: "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Torres_del_Paine_-_Chile.jpg/480px-Torres_del_Paine_-_Chile.jpg",
  singapore: "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Singapore_Skyline_2019-05-13_panorama.jpg/480px-Singapore_Skyline_2019-05-13_panorama.jpg",
  marrakech: "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Djemaa_el_Fna_at_night.jpg/480px-Djemaa_el_Fna_at_night.jpg",
  phuket: "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Phuket_Patong_Beach.jpg/480px-Phuket_Patong_Beach.jpg",
  "costa rica": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/Manuel_Antonio_National_Park_Costa_Rica.jpg/480px-Manuel_Antonio_National_Park_Costa_Rica.jpg",
};

const FALLBACK = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Traveller.jpg/480px-Traveller.jpg";

const SECTION_WORDS = /\b(tips|tip|activities|activity|budget|note|notes|season|weather|exchange|rate|rates|cost|costs|practical|recommended|highlights|overview|summary|itinerary|accommodation|transport|visa|currency|day|week|month|why|best|top|key|main|important|getting|around|things|to|do|see|know|before|you|go|travel|style|request|suit|these|your)\b/i;

export function extractDestinations(markdown: string): string[] {
  const matches = markdown.matchAll(/\*\*([^*]{2,40})\*\*/g);
  const seen = new Set<string>();
  const results: string[] = [];
  for (const m of matches) {
    const name = m[1].trim();
    if (
      seen.has(name) ||
      name.endsWith(":") ||
      name.endsWith(".") ||
      /^\d/.test(name) ||
      /^\$/.test(name) ||
      !/^[A-Z]/.test(name) ||
      SECTION_WORDS.test(name)
    ) continue;
    seen.add(name);
    results.push(name);
  }
  return results.slice(0, 6);
}

function imageFor(name: string): string {
  const key = name.toLowerCase();
  for (const [k, url] of Object.entries(IMAGES)) {
    if (key.includes(k) || k.includes(key)) return url;
  }
  return FALLBACK;
}

interface Props {
  markdown: string;
  onSelect: (destination: string) => void;
}

export default function DestinationCards({ markdown, onSelect }: Props) {
  const destinations = extractDestinations(markdown);
  if (destinations.length === 0) return null;

  return (
    <div className="mt-4">
      <p className="text-xs font-semibold uppercase tracking-widest mb-2.5" style={{ color: "#94a3b8" }}>
        Destinations mentioned
      </p>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {destinations.map((dest) => (
          <button
            key={dest}
            onClick={() => onSelect(dest)}
            className="flex-shrink-0 w-36 rounded-xl overflow-hidden shadow-sm hover:shadow-lg transition-all text-left group"
            style={{ border: "1px solid #e2e8f0" }}
          >
            <div className="relative h-24 overflow-hidden">
              <img
                src={imageFor(dest)}
                alt={dest}
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                onError={(e) => { (e.target as HTMLImageElement).src = FALLBACK; }}
              />
              <div className="absolute inset-0"
                   style={{ background: "linear-gradient(to top, rgba(0,0,0,0.55) 0%, transparent 60%)" }} />
              <p className="absolute bottom-1.5 left-2 right-2 text-white text-xs font-semibold truncate drop-shadow">
                {dest}
              </p>
            </div>
            <div className="px-2.5 py-2 bg-white">
              <p className="text-xs font-medium transition" style={{ color: "#4f46e5" }}>
                Explore →
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
