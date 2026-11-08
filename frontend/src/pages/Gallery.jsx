import React from 'react';
import SectionTitle from '../components/SectionTitle.jsx';
import gallery from '../data/gallery.js';

export default function Gallery() {
  return (
    <section className="section container page-section">
      <SectionTitle eyebrow="Gallery" title="Moments that bring us together" description="A glimpse of the people, places, and shared experiences that make our community." />
      <div className="gallery-grid">
        {gallery.map((item) => (
          <figure className={`gallery-tile ${item.tone}`} key={item.id}>
            <div className="gallery-placeholder" aria-hidden="true">{item.number}</div>
            <figcaption>{item.caption}</figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}
