import React, { useState } from 'react';
import { User, Mail, Shield, Smartphone, Bell, Moon, Database, Activity, Lock, Share2, TrendingUp, AlertTriangle } from 'lucide-react';

export function ProfileView() {
  return (
    <div className="flex-1 overflow-y-auto p-12 bg-slate-50 dark:bg-[#0A1128] text-slate-800 dark:text-gray-200">
      <div className="max-w-4xl mx-auto space-y-8 animate-fade-in relative">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-orange-400 to-red-500">
          User Profile
        </h1>
        
        <div className="bg-slate-800/50 backdrop-blur-md rounded-2xl p-8 border border-slate-700/50 shadow-xl flex gap-8 items-center relative overflow-hidden">
          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center shadow-lg shadow-orange-500/20">
            <User size={40} className="text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Guest Commander</h2>
            <p className="text-slate-400 flex items-center gap-2 mt-1">
              <Mail size={16} /> commander@saferoute.ai
            </p>
            <div className="mt-4 flex gap-4">
              <span className="px-3 py-1 bg-green-500/10 text-green-400 rounded-full text-xs font-semibold border border-green-500/20">Active Pro</span>
              <span className="px-3 py-1 bg-blue-500/10 text-blue-400 rounded-full text-xs font-semibold border border-blue-500/20">Elite Navigator</span>
            </div>
          </div>
          <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-white/5 to-transparent rounded-full -translate-y-1/2 translate-x-1/2 blur-2xl pointer-events-none"></div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <StatCard title="Safe Miles Traveled" value="1,204" icon={<Activity className="text-blue-400" />} />
          <StatCard title="High-Risk Zones Avoided" value="142" icon={<Shield className="text-orange-400" />} />
        </div>
      </div>
    </div>
  );
}

export function SettingsView({ globalDarkMode, setGlobalDarkMode }) {
  const [preferences, setPreferences] = useState({
    darkMode: globalDarkMode !== undefined ? globalDarkMode : true,
    realTimeAlerts: true,
    autoRerouting: false,
    anonymousMode: false,
    crowdSourcing: true
  });

  const togglePreference = async (key) => {
    const newVal = !preferences[key];
    setPreferences(prev => ({ ...prev, [key]: newVal }));
    
    if (key === 'darkMode' && setGlobalDarkMode) {
      setGlobalDarkMode(newVal);
    }
    
    // Call backend to save setting
    try {
      await fetch('http://localhost:8000/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value: newVal })
      });
    } catch (e) {
      console.warn("Backend not fully reachable for settings save", e);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-12 bg-slate-50 dark:bg-[#0A1128] text-slate-800 dark:text-gray-200">
      <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-500">
          System Settings
        </h1>

        <div className="space-y-6">
          <SettingsSection title="Preferences" icon={<Smartphone size={20} />}>
            <ToggleOption label="Dark Mode" description="Use dark theme across all maps and dashboards." enabled={preferences.darkMode} onClick={() => togglePreference('darkMode')} />
            <ToggleOption label="Real-time Alerts" description="Receive push notifications when entering high-risk areas." enabled={preferences.realTimeAlerts} onClick={() => togglePreference('realTimeAlerts')} />
            <ToggleOption label="Auto-Rerouting" description="Automatically divert route if live risk spike is detected." enabled={preferences.autoRerouting} onClick={() => togglePreference('autoRerouting')} />
          </SettingsSection>
          
          <SettingsSection title="Privacy & Data" icon={<Lock size={20} />}>
            <ToggleOption label="Anonymous Mode" description="Hide your telemetry from global heatmaps." enabled={preferences.anonymousMode} onClick={() => togglePreference('anonymousMode')} />
            <ToggleOption label="Crowd-Sourcing" description="Share local incident reports to improve AI accuracy." enabled={preferences.crowdSourcing} onClick={() => togglePreference('crowdSourcing')} />
          </SettingsSection>
        </div>
      </div>
    </div>
  );
}

export function AnalyticsDashboard() {
  return (
    <div className="flex-1 overflow-y-auto p-12 bg-slate-50 dark:bg-[#0A1128] text-slate-800 dark:text-gray-200">
      <div className="max-w-5xl mx-auto space-y-8 animate-fade-in relative">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-teal-500">
            Global Analytics & Intelligence
          </h1>
          <button className="px-4 py-2 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 rounded-lg text-sm transition-colors border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white">Export Report</button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard title="Total Predictions" value="1.4M" icon={<Database className="text-emerald-400" />} />
          <StatCard title="Model Accuracy" value="94.2%" icon={<TrendingUp className="text-teal-400" />} />
          <StatCard title="Active Incidents" value="8,402" icon={<AlertTriangle className="text-red-400" />} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <div className="bg-slate-800/40 rounded-2xl p-6 border border-slate-700/50">
            <h3 className="text-lg font-semibold mb-6 flex items-center gap-2"><Activity size={18} className="text-indigo-400"/> AI Engine Distribution</h3>
            <div className="space-y-4">
              <ProgressBar label="XGBoost Tabular Core" percentage={45} color="bg-indigo-500" />
              <ProgressBar label="LightGBM Mobility" percentage={35} color="bg-cyan-500" />
              <ProgressBar label="PyTorch CNN (Nightlights)" percentage={20} color="bg-purple-500" />
            </div>
          </div>
          
          <div className="bg-slate-800/40 rounded-2xl p-6 border border-slate-700/50">
            <h3 className="text-lg font-semibold mb-6 flex items-center gap-2"><AlertTriangle size={18} className="text-orange-400"/> Recent Risk Spikes</h3>
            <div className="space-y-3">
              <RiskSpike location="Downtown Financial District" time="2 mins ago" risk="89/100" />
              <RiskSpike location="Westside Industrial Park" time="14 mins ago" risk="74/100" />
              <RiskSpike location="Northern Suburbs Transit" time="1 hour ago" risk="65/100" />
              <RiskSpike location="University Campus East" time="3 hours ago" risk="58/100" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ------ Helper Components ------

function StatCard({ title, value, icon }) {
  return (
    <div className="bg-white dark:bg-slate-800/40 rounded-xl p-6 border border-slate-200 dark:border-slate-700/50 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors shadow-sm dark:shadow-none">
      <div>
        <p className="text-slate-500 dark:text-slate-400 text-sm font-medium mb-1">{title}</p>
        <h3 className="text-3xl font-bold text-slate-900 dark:text-white">{value}</h3>
      </div>
      <div className="p-4 bg-slate-100 dark:bg-slate-900/50 rounded-full border border-slate-200 dark:border-slate-700/30">
        {icon}
      </div>
    </div>
  );
}

function SettingsSection({ title, icon, children }) {
  return (
    <div className="bg-slate-800/40 rounded-2xl border border-slate-700/50 overflow-hidden">
      <div className="px-6 py-4 bg-slate-900/30 border-b border-slate-700/50 flex items-center gap-2">
        <span className="text-slate-400">{icon}</span>
        <h3 className="font-semibold text-white">{title}</h3>
      </div>
      <div className="divide-y divide-slate-700/50">
        {children}
      </div>
    </div>
  );
}

function ToggleOption({ label, description, enabled, onClick }) {
  return (
    <div className="px-6 py-5 flex items-center justify-between hover:bg-slate-800/30 transition-colors cursor-pointer select-none" onClick={onClick}>
      <div>
        <h4 className="font-medium text-white">{label}</h4>
        <p className="text-sm text-slate-400 mt-1">{description}</p>
      </div>
      <div className={`w-12 h-6 rounded-full transition-colors relative ${enabled ? 'bg-orange-500' : 'bg-slate-600'}`}>
        <div className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full transition-transform duration-200 ${enabled ? 'translate-x-6' : 'translate-x-0'}`}></div>
      </div>
    </div>
  );
}

function ProgressBar({ label, percentage, color }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-2">
        <span className="text-slate-300">{label}</span>
        <span className="text-white font-medium">{percentage}%</span>
      </div>
      <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden">
        <div className={`${color} h-2.5 rounded-full transition-all duration-1000`} style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
}

function RiskSpike({ location, time, risk }) {
  return (
    <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded-lg border border-slate-700/30 hover:border-slate-600 transition-colors">
      <div>
        <h4 className="text-white text-sm font-medium">{location}</h4>
        <p className="text-xs text-slate-500 mt-0.5">{time}</p>
      </div>
      <div className="bg-orange-500/10 text-orange-400 px-3 py-1 rounded-md text-sm font-bold border border-orange-500/20">
        {risk}
      </div>
    </div>
  );
}
