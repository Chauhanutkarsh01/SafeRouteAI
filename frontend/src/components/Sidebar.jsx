import React from 'react';
import { Compass, BarChart2, Shield, Settings, User } from 'lucide-react';

export default function Sidebar({ safetyMode, setSafetyMode, activeTab, setActiveTab }) {
  return (
    <div className="w-16 hover:w-48 group/sidebar transition-all duration-300 ease-in-out bg-white dark:bg-dark-navy border-r border-gray-200 dark:border-roads flex flex-col py-4 z-50 overflow-hidden">
      <div className="flex flex-col gap-8 w-full mt-4 flex-1">
        <NavButton icon={<Compass size={24} />} label="Navigation" active={activeTab === 'map'} onClick={() => setActiveTab('map')} />
        <NavButton icon={<BarChart2 size={24} />} label="Analytics" active={activeTab === 'analytics'} onClick={() => setActiveTab('analytics')} />
        <NavButton 
          icon={<Shield size={24} className={safetyMode ? "text-accent" : ""} />} 
          label="Safety Mode" 
          onClick={() => setSafetyMode(!safetyMode)} 
          active={safetyMode}
        />
      </div>
      
      <div className="flex flex-col gap-6 w-full mb-4">
        <NavButton icon={<Settings size={24} />} label="Settings" active={activeTab === 'settings'} onClick={() => setActiveTab('settings')} />
        <NavButton icon={<User size={24} />} label="Profile" active={activeTab === 'profile'} onClick={() => setActiveTab('profile')} />
      </div>
    </div>
  );
}

function NavButton({ icon, label, onClick, active }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center relative hover:text-accent transition-colors px-5 ${active ? 'text-accent' : 'text-slate-500 dark:text-text-light'}`}
    >
      <div className="min-w-fit">{icon}</div>
      <span className="ml-4 opacity-0 group-hover/sidebar:opacity-100 whitespace-nowrap text-sm font-medium transition-opacity">
        {label}
      </span>
    </button>
  );
}
