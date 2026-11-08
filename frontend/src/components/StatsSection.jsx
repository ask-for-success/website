import React from 'react';
const stats = [
  { value: '1,200+', label: 'Students supported' },
  { value: '40+', label: 'Events organized' },
  { value: '25+', label: 'Partners & Sponsors' },
  { value: '300+', label: 'Active volunteers' },
];

export default function StatsSection() {
  return (
    <section className="stats-section" aria-label="Our impact">

      {/* Decorative lines */}
      <div className="stats-decoration stats-decoration-left" aria-hidden="true">
        {Array.from({ length: 7 }, (_, i) => (
          <span key={i}></span>
        ))}
      </div>

      <div className="container stats-grid">
        {stats.map((stat) => (
          <div className="stat" key={stat.label}>
            <strong>{stat.value}</strong>
            <span>{stat.label}</span>
          </div>
        ))}
      </div>

      <div className="stats-decoration stats-decoration-right" aria-hidden="true">
        {Array.from({ length: 7 }, (_, i) => (
          <span key={i}></span>
        ))}
      </div>

    </section>
  );
}
