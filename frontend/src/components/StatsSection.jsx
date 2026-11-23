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
      <img
        className="stats-decoration stats-decoration-left"
        src="/assets/images/stats/stats-left.svg"
        alt=""
      />
      <div className="site-shell stats-grid">
        {stats.map((stat) => (
          <div className="stat" key={stat.label}>
            <strong>{stat.value}</strong>
            <span>{stat.label}</span>
          </div>
        ))}
      </div>

      <img
        className="stats-decoration stats-decoration-right"
        src="/assets/images/stats/stats-right.svg"
        alt=""
      />
    </section>
  );
}
