import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMap } from 'react-leaflet';
import axios from 'axios';
import { Navigation } from 'lucide-react';
import L from 'leaflet';

// Fix for default Leaflet marker icons with Vite
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

function ChangeView({ center, zoom }) {
  const map = useMap();
  map.setView(center, zoom);
  return null;
}

export default function LeafletMapContainer({ safetyMode, onRouteSelect }) {
  // default India coordinates for broad view, but source/dest set to Tamil Nadu
  const [center, setCenter] = useState([13.0827, 80.2707]);
  const [zoom, setZoom] = useState(12);

  const [source, setSource] = useState({ lat: 13.0827, lon: 80.2707 }); // Chennai Central
  const [destination, setDestination] = useState({ lat: 12.9716, lon: 80.2496 }); // Velachery
  const [sourceText, setSourceText] = useState("Chennai Central, Tamil Nadu");
  const [destText, setDestText] = useState("Velachery, Tamil Nadu");
  
  const [sourceSuggestions, setSourceSuggestions] = useState([]);
  const [destSuggestions, setDestSuggestions] = useState([]);
  const [activeInput, setActiveInput] = useState(null); // 'source' or 'dest'
  
  const [sliderValue, setSliderValue] = useState(50); // 0 = Safest, 100 = Fastest
  const [routeCoords, setRouteCoords] = useState([]);
  const [loading, setLoading] = useState(false);

  const getPreference = (val) => {
    if (val < 33) return 'safest';
    if (val > 66) return 'fastest';
    return 'balanced';
  };

  const getRouteColor = (preference) => {
    if (preference === 'safest') return '#22c55e'; // Green
    if (preference === 'fastest') return '#3b82f6'; // Blue
    return '#eab308'; // Yellow
  };

  const sourceTimer = useRef(null);
  const destTimer = useRef(null);

  const fetchSuggestions = async (query, setSuggestions) => {
    if (!query || query.length < 3) {
      setSuggestions([]);
      return;
    }
    try {
      const res = await axios.get(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ', Tamil Nadu')}&countrycodes=in&limit=5&email=saferoute_api@test.com`, {
        headers: { 'Accept-Language': 'en-US,en;q=0.9' }
      });
      setSuggestions(res.data || []);
    } catch (err) {
      console.error("Suggestions failed", err);
      // Fails silently if rate limited
      setSuggestions([]);
    }
  };

  const handleSourceChange = (e) => {
    setSourceText(e.target.value);
    setSource(null); // invalidate current source
    if (sourceTimer.current) clearTimeout(sourceTimer.current);
    sourceTimer.current = setTimeout(() => {
      fetchSuggestions(e.target.value, setSourceSuggestions);
    }, 1000); // 1 sec debounce
  };
  
  const handleDestChange = (e) => {
    setDestText(e.target.value);
    setDestination(null); // invalidate current destination
    if (destTimer.current) clearTimeout(destTimer.current);
    destTimer.current = setTimeout(() => {
      fetchSuggestions(e.target.value, setDestSuggestions);
    }, 1000);
  };

  const selectSuggestion = (point, isSource) => {
    const lat = parseFloat(point.lat);
    const lon = parseFloat(point.lon);
    if (isSource) {
      setSourceText(point.display_name);
      setSource({ lat, lon });
      setSourceSuggestions([]);
      setActiveInput(null);
    } else {
      setDestText(point.display_name);
      setDestination({ lat, lon });
      setDestSuggestions([]);
      setActiveInput(null);
    }
  };

  const geocode = async (query) => {
    try {
      const res = await axios.get(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ', Tamil Nadu')}&countrycodes=in&limit=1&email=saferoute_api@test.com`, {
        headers: { 'Accept-Language': 'en-US,en;q=0.9' }
      });
      if (res.data && res.data.length > 0) {
        return { lat: parseFloat(res.data[0].lat), lon: parseFloat(res.data[0].lon) };
      }
    } catch (err) {
      console.error("Geocoding failed for", query);
    }
    return null;
  };

  const fetchRoute = async () => {
    setLoading(true);
    
    // Geocode A
    let parsedSource = source;
    if (!parsedSource) {
      parsedSource = await geocode(sourceText);
      if (!parsedSource) {
        setLoading(false);
        return alert(`Could not locate origin: ${sourceText}\n(Please wait a moment if you typed too fast)`);
      }
    }
    
    // Geocode B
    let parsedDest = destination;
    if (!parsedDest) {
      parsedDest = await geocode(destText);
      if (!parsedDest) {
        setLoading(false);
        return alert(`Could not locate destination: ${destText}\n(Please wait a moment if you typed too fast)`);
      }
    }
    
    setSource(parsedSource);
    setDestination(parsedDest);

    try {
      const preference = getPreference(sliderValue);
      const res = await axios.post('http://localhost:8000/route', {
        start: parsedSource,
        end: parsedDest,
        preference: preference
      }, { timeout: 60000 }); // 60 second timeout
      
      const coords = res.data.route.map(pos => [pos.lat, pos.lon]);
      setRouteCoords(coords);
      
      // Use real risk score from backend
      const avgRisk = res.data.avg_risk || 50.0;
      onRouteSelect({ preference, avgRisk });

      // Automatically bound map to route if coords exist
      if (coords.length > 0) {
        setCenter(coords[Math.floor(coords.length / 2)]);
        setZoom(13);
      }
    } catch (err) {
      console.error("Failed to fetch route:", err);
      const serverMessage = err.response?.data?.detail;
      alert(`Routing Error: ${serverMessage || "Failed to fetch route. Is backend running?"}`);
    } finally {
      setLoading(false);
    }
  };

  // World Imagery (Satellite) Map from Esri
  const tileUrl = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

  return (
    <div className="w-full h-full relative">
      <MapContainer 
        center={center} 
        zoom={zoom} 
        style={{ width: '100%', height: '100%', zIndex: 0 }}
      >
        <ChangeView center={center} zoom={zoom} />
        <TileLayer
          attribution='&copy; <a href="https://www.esri.com/">Esri</a>, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
          url={tileUrl}
        />
        
        {source && <Marker position={[source.lat, source.lon]} />}
        {destination && <Marker position={[destination.lat, destination.lon]} />}

        {routeCoords.length > 0 && (
          <Polyline 
            positions={routeCoords} 
            color={getRouteColor(getPreference(sliderValue))} 
            weight={6} 
            opacity={0.8}
          />
        )}
      </MapContainer>

      {/* Floating Bottom Control Panel */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 bg-white/90 dark:bg-[#1E293B]/90 backdrop-blur-md p-6 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-2xl w-[28rem] z-10">
        <div className="flex gap-4 items-center">
          <div className="flex-1 space-y-3 relative">
             <div className="flex flex-col relative w-full">
               <div className="flex bg-slate-50 dark:bg-dark-navy p-2 rounded-lg border border-slate-300 dark:border-gray-700 focus-within:border-accent z-20">
                 <span className="text-green-500 mr-2 px-1">A</span>
                 <input 
                   value={sourceText} 
                   onChange={handleSourceChange}
                   onFocus={() => setActiveInput('source')}
                   placeholder="Search start location..."
                   className="bg-transparent outline-none w-full text-sm text-slate-800 dark:text-gray-300"
                 />
               </div>
               
               {activeInput === 'source' && sourceSuggestions.length > 0 && (
                 <ul className="absolute top-full left-0 w-full mt-1 bg-white dark:bg-gray-800 border border-slate-200 dark:border-gray-600 rounded-lg shadow-xl z-30 max-h-48 overflow-y-auto">
                   {sourceSuggestions.map((s, idx) => (
                     <li key={idx} onMouseDown={() => selectSuggestion(s, true)} className="p-2 text-xs cursor-pointer hover:bg-slate-100 dark:hover:bg-gray-700 text-slate-700 dark:text-gray-300 border-b border-slate-200 dark:border-gray-700 last:border-0 truncate">
                       {s.display_name}
                     </li>
                   ))}
                 </ul>
               )}
             </div>

             <div className="flex flex-col relative w-full">
               <div className="flex bg-slate-50 dark:bg-dark-navy p-2 rounded-lg border border-slate-300 dark:border-gray-700 focus-within:border-accent z-10">
                 <span className="text-red-500 mr-2 px-1">B</span>
                 <input 
                   value={destText} 
                   onChange={handleDestChange}
                   onFocus={() => setActiveInput('dest')}
                   placeholder="Search destination..."
                   className="bg-transparent outline-none w-full text-sm text-slate-800 dark:text-gray-300"
                 />
               </div>
               
               {activeInput === 'dest' && destSuggestions.length > 0 && (
                 <ul className="absolute top-full left-0 w-full mt-1 bg-white dark:bg-gray-800 border border-slate-200 dark:border-gray-600 rounded-lg shadow-xl z-30 max-h-48 overflow-y-auto">
                   {destSuggestions.map((s, idx) => (
                     <li key={idx} onMouseDown={() => selectSuggestion(s, false)} className="p-2 text-xs cursor-pointer hover:bg-slate-100 dark:hover:bg-gray-700 text-slate-700 dark:text-gray-300 border-b border-slate-200 dark:border-gray-700 last:border-0 truncate">
                       {s.display_name}
                     </li>
                   ))}
                 </ul>
               )}
             </div>
          </div>
          <button 
            onClick={fetchRoute}
            disabled={loading}
            className="w-16 h-16 bg-accent hover:bg-orange-500 transition shadow-lg shadow-accent/20 rounded-full flex justify-center items-center text-white"
          >
            <Navigation size={24} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Safety vs Speed Slider */}
        <div className="mt-6 pt-4 border-t border-slate-200 dark:border-gray-700/50">
          <div className="flex justify-between text-xs text-gray-400 font-semibold mb-2 uppercase tracking-widest">
            <span className="text-green-400">Safest</span>
            <span className="text-yellow-400">Balanced</span>
            <span className="text-blue-400">Fastest</span>
          </div>
          <input 
            type="range" 
            min="0" max="100" 
            value={sliderValue}
            onChange={(e) => setSliderValue(e.target.value)}
            className="w-full h-2 bg-slate-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-accent"
          />
        </div>
      </div>
    </div>
  );
}
