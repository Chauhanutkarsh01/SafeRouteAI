import React from 'react';

export default function AnalyticsPanel({ selectedRoute }) {
  return (
    <div className="w-80 bg-white dark:bg-dark-navy border-l border-gray-200 dark:border-roads flex flex-col p-6 z-40 overflow-y-auto">
      <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
        <span className="text-accent">📊</span> Analytics
      </h2>
      
      {selectedRoute ? (
        <div className="space-y-6">
          <div className="p-4 bg-slate-100 dark:bg-roads rounded-xl">
            <h3 className="text-sm text-slate-500 dark:text-gray-400 capitalize">{selectedRoute.preference} Route</h3>
            <p className="text-2xl font-bold mt-1">
              Risk: {selectedRoute.avgRisk.toFixed(1)} / 100
            </p>
          </div>
          
          <div>
            <h3 className="text-sm font-semibold mb-3">Event Composition</h3>
            <ProgressBar label="Dangerous Intersections" percentage={selectedRoute.avgRisk * 0.4} color="bg-orange-500" />
            <ProgressBar label="Lighting Issues" percentage={selectedRoute.avgRisk * 0.3} color="bg-yellow-500" />
            <ProgressBar label="Pedestrian Incidents" percentage={selectedRoute.avgRisk * 0.3} color="bg-red-500" />
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-500 py-10">
          <p>Please enter a source and destination to view risk analytics.</p>
        </div>
      )}
    </div>
  );
}

function ProgressBar({ label, percentage, color }) {
  return (
    <div className="mb-4">
      <div className="flex justify-between text-xs mb-1">
        <span>{label}</span>
        <span>{percentage.toFixed(1)}%</span>
      </div>
      <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all duration-1000 ease-out`} style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
}
