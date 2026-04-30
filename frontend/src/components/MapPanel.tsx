import { Component, useEffect, useRef } from "react";
import L from "leaflet";
import { GeoResult } from "../api/client";

// Destination marker (red)
const DEST_ICON = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

/** Great-circle distance in km using Haversine formula */
function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/** Format km distance as flight time string */
function flightTime(km: number): string {
  const hrs = km / 900; // average cruise ~900 km/h
  const total = hrs + 1.5; // +1.5h airport overhead
  const h = Math.floor(total);
  const m = Math.round((total - h) * 60);
  return `~${h}h ${m > 0 ? m + "m" : ""}`.trim();
}

// ── Error boundary ────────────────────────────────────────────────────────────
interface BState { hasError: boolean }
class MapErrorBoundary extends Component<{ children: React.ReactNode }, BState> {
  state: BState = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  render() {
    if (this.state.hasError)
      return <div className="h-40 flex items-center justify-center text-sm text-gray-400 bg-gray-50 rounded-xl">Map unavailable.</div>;
    return this.props.children;
  }
}

// ── Main map component ────────────────────────────────────────────────────────
export interface UserLocation { lat: number; lng: number; city?: string }

interface Props {
  locations: GeoResult[];          // destination pins
  userLocation: UserLocation | null;
  onMarkerClick: (name: string) => void;
}

function MapInner({ locations, userLocation, onMarkerClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (locations.length === 0 && !userLocation) return;

    // Build map fresh on every dependency change
    const map = L.map(containerRef.current, { scrollWheelZoom: false });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18,
    }).addTo(map);

    const allLatLngs: L.LatLngTuple[] = [];

    // User location — blue circle
    if (userLocation) {
      L.circleMarker([userLocation.lat, userLocation.lng], {
        radius: 9,
        color: "#2563eb",
        fillColor: "#3b82f6",
        fillOpacity: 0.8,
        weight: 2,
      })
        .addTo(map)
        .bindPopup(`<strong>Your location</strong>${userLocation.city ? `<br>${userLocation.city}` : ""}`);
      allLatLngs.push([userLocation.lat, userLocation.lng]);
    }

    // Destination markers + route lines
    locations.forEach((loc) => {
      L.marker([loc.lat, loc.lng], { icon: DEST_ICON })
        .addTo(map)
        .bindPopup(
          `<strong>${loc.name}</strong>${
            userLocation
              ? `<br><span style="color:#6b7280;font-size:11px">
                  ${Math.round(haversineKm(userLocation.lat, userLocation.lng, loc.lat, loc.lng)).toLocaleString()} km
                  &nbsp;·&nbsp;${flightTime(haversineKm(userLocation.lat, userLocation.lng, loc.lat, loc.lng))} flight
                 </span>`
              : ""
          }`
        )
        .on("click", () => onMarkerClick(loc.name));

      allLatLngs.push([loc.lat, loc.lng]);

      // Dashed route line from user to destination
      if (userLocation) {
        L.polyline(
          [[userLocation.lat, userLocation.lng], [loc.lat, loc.lng]],
          { color: "#3b82f6", dashArray: "8 12", weight: 2, opacity: 0.7 }
        ).addTo(map);
      }
    });

    // Fit map to show everything
    if (allLatLngs.length === 1) {
      map.setView(allLatLngs[0], 10);
    } else if (allLatLngs.length > 1) {
      map.fitBounds(allLatLngs, { padding: [30, 30] });
    }

    return () => { map.remove(); };
  }, [locations, userLocation, onMarkerClick]);

  if (locations.length === 0 && !userLocation) return null;

  return (
    <div>
      <div ref={containerRef} style={{ height: "220px", width: "100%" }} />
      {userLocation && locations.length > 0 && (
        <div className="px-3 py-2 flex flex-wrap gap-2" style={{ background: "#f8fafc", borderTop: "1px solid #e2e8f0" }}>
          {locations.map((loc) => {
            const km = Math.round(haversineKm(userLocation.lat, userLocation.lng, loc.lat, loc.lng));
            return (
              <span key={loc.name} className="text-xs text-slate-500">
                <span className="font-medium text-slate-700">{loc.name}</span>
                {" · "}{km.toLocaleString()} km · {flightTime(km)}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function MapPanel(props: Props) {
  return <MapErrorBoundary><MapInner {...props} /></MapErrorBoundary>;
}
