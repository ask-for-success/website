import React from 'react';
export default function SectionTitle({ eyebrow, title, description, centered = false }) {
  return (
    <div className={`section-title${centered ? ' section-title-centered' : ''}`}>
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h2>{title}</h2>
      {description && <p className="section-description">{description}</p>}
    </div>
  );
}
