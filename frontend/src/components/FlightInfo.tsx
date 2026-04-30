interface Props {
  defaultDestination?: string;
}

export default function FlightInfo({ defaultDestination = "" }: Props) {
  const params = new URLSearchParams({ type: "ONEWAY", adults: "1" });
  if (defaultDestination) params.set("to", defaultDestination);
  const href = `https://www.booking.com/flights/search.html?${params.toString()}`;

  return (
    <div className="bg-white rounded-2xl shadow-sm overflow-hidden" style={{ border: "1px solid #e2e8f0" }}>
      <div className="px-4 py-3 flex items-center gap-3"
           style={{ background: "linear-gradient(135deg, #0c4a6e, #0369a1)" }}>
        <span className="text-xl">✈</span>
        <div>
          <p className="text-sm font-semibold text-white">Find Flights</p>
          <p className="text-xs text-sky-200">Live prices via Booking.com</p>
        </div>
      </div>
      <div className="px-4 py-3">
        <p className="text-xs text-slate-500 mb-3 leading-relaxed">
          For the most up-to-date prices and availability, search directly on Booking.com.
        </p>
        <a href={href} target="_blank" rel="noopener noreferrer"
          className="block w-full text-center text-white text-sm font-semibold py-2.5 rounded-xl transition hover:opacity-90"
          style={{ background: "linear-gradient(135deg, #0369a1, #0284c7)" }}>
          Search Flights ↗
        </a>
      </div>
    </div>
  );
}
