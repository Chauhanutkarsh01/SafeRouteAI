import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import AnalyticsPanel from './components/AnalyticsPanel';
import MapContainer from './components/MapContainer';
import { SettingsView, ProfileView, AnalyticsDashboard } from './components/Views';

export default function App() {
  const [safetyMode, setSafetyMode] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [activeTab, setActiveTab] = useState('map');
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);
  
  return (
    <div className="flex h-screen w-full bg-slate-50 text-slate-900 dark:bg-dark-navy dark:text-text-light overflow-hidden">
      {/* Left Navigation */}
      <Sidebar 
        safetyMode={safetyMode} 
        setSafetyMode={setSafetyMode} 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
      />

      {/* Main Content Area */}
      {activeTab === 'map' && (
        <>
          <div className="flex-1 relative h-full">
            <MapContainer safetyMode={safetyMode} onRouteSelect={setSelectedRoute} />
          </div>
          {/* Right Analytics Panel only on Maps */}
          <AnalyticsPanel selectedRoute={selectedRoute} />
        </>
      )}

      {activeTab === 'analytics' && <AnalyticsDashboard />}
      {activeTab === 'settings' && <SettingsView globalDarkMode={darkMode} setGlobalDarkMode={setDarkMode} />}
      {activeTab === 'profile' && <ProfileView />}

    </div>
  );
}
