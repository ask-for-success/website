import React, { useState } from 'react';

const categories = ['All', 'Summits', 'Workshops', 'Outreach', 'Community', 'Behind the scenes'];
const workshopImage = '/assets/images/gallery/Youth Summit 2026.png';
const photos = [
  { id: 1, image: workshopImage, title: 'Youth Summit 2026', category: 'Summits',
    height: 420, alt: 'Students gathered around workshop equipment' },
  { id: 2, image: '/assets/images/gallery/Atlas outreach day.jpg', title: 'Atlas outreach day',
    category: 'Outreach', height: 300, alt: 'A group holding flags in the Atlas Mountains' },
  { id: 3, image: '/assets/images/gallery/Opening day.png', title: 'Opening day',
    category: 'Community', height: 380, alt: 'Volunteers unpacking donations' },
  { id: 4, image: '/assets/images/gallery/Flag ceremony, Ain Chok.jpg', title: 'Flag ceremony, Ain Chok',
    category: 'Community', height: 300, alt: 'A volunteer working with children' },
  { id: 5, image: workshopImage, title: 'Lycée workshop, Casablanca', category: 'Workshops',
    height: 460, alt: 'Students gathered around workshop equipment' },
  { id: 6, image: '/assets/images/gallery/children2.jpg', title: 'Youth Summit 2026',
    category: 'Outreach', height: 320, alt: 'Children and volunteers posing together' },
  { id: 7, image: '/assets/images/gallery/Volunteer team.jpg', title: 'Volunteer team',
    category: 'Behind the scenes', height: 360, alt: 'A volunteer holding a long-handled tool' },
  { id: 8, image: '/assets/images/gallery/children1.jpg', title: 'Youth Summit 2026',
    category: 'Community', height: 320, alt: 'Students smiling together' },
  { id: 9, image: '/assets/images/gallery/Graduation 2025.jpg', title: 'Graduation 2025',
    category: 'Community', height: 380, alt: 'Children posing beneath a decorated stage' },
];

const highlights = [
  {
    id: 'youth-summit-aftermovie', image: '/assets/images/gallery/vedio1.png',
    title: 'Youth Summit 2026 — aftermovie', duration: '3 min', date: 'October 2026', dateTime: '2026-10',
  },
  {
    id: 'atlas-day', image: '/assets/images/gallery/vedio2.jpg',
    title: 'A day in the Atlas with AFS', duration: '5 min', date: 'June 2026', dateTime: '2026-06',
  },
];

const INITIAL_COUNT = 9;
const LOAD_COUNT = 6;

export default function Gallery() {
  const [activeCategory, setActiveCategory] = useState('All');
  const [visibleCount, setVisibleCount] = useState(INITIAL_COUNT);
  const filteredPhotos = activeCategory === 'All'
    ? photos
    : photos.filter((photo) => photo.category === activeCategory);

  function changeCategory(category) {
    setActiveCategory(category);
    setVisibleCount(INITIAL_COUNT);
  }

  const columns = [[], [], []];
  filteredPhotos.slice(0, visibleCount).forEach((photo, index) => {
    columns[index % 3].push(photo);
  });

  return (
    <>
      <section className="gallery-hero" aria-labelledby="gallery-title">
        <div className="site-shell listing-intro">
          <h1 id="gallery-title">Moments that tell our <span>story</span>.</h1>
          <p>
            Summits, workshops and outreach days across Morocco, captured by our volunteers
            and the students themselves.
          </p>
        </div>
      </section>

      <section className="gallery-content" aria-label="Photos">
        <div className="site-shell">
          <div className="gallery-filters" role="group" aria-label="Gallery filters">
            {categories.map((category) => (
              <button
                key={category}
                type="button"
                className="listing-chip gallery-filter"
                onClick={() => changeCategory(category)}
                aria-pressed={activeCategory === category}
              >
                {category}
              </button>
            ))}
          </div>

          <div className="afs-gallery-grid" aria-live="polite">
            {columns.map((column, columnIndex) => (
              <div className="afs-gallery-column" key={columnIndex}>
                {column.map((photo) => (
                  <figure
                    className="afs-gallery-item"
                    key={photo.id}
                    style={{ '--gallery-tile-height': photo.height }}
                  >
                    <img src={photo.image} alt={photo.alt} loading="lazy" />
                    <figcaption className="afs-gallery-caption">{photo.title}</figcaption>
                  </figure>
                ))}
              </div>
            ))}
          </div>

          {filteredPhotos.length === 0 && (
            <p className="gallery-empty">No photos available in this category yet.</p>
          )}

          {filteredPhotos.length > 0 && (
            <div className="gallery-load-more">
              <button
                type="button"
                className="home-button home-button--large home-button--outline gallery-load-button"
                disabled={visibleCount >= filteredPhotos.length}
                onClick={() => setVisibleCount((count) => Math.min(count + LOAD_COUNT, filteredPhotos.length))}
              >
                Load more photos
                <img src="/assets/icons/home/arrow-outlined.svg" alt="" />
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="gallery-highlights" aria-labelledby="gallery-highlights-title">
        <div className="site-shell">
          <header className="listing-section-title">
            <h2 id="gallery-highlights-title">Watch the highlights</h2>
            <p>Short films made by our media volunteers.</p>
          </header>

          <div className="gallery-highlights-grid">
            {highlights.map((highlight) => (
              <article className="gallery-highlight-card" key={highlight.id}>
                <div className="gallery-highlight-media">
                  <img src={highlight.image} alt="" loading="lazy" />
                  <button
                    className="gallery-highlight-play"
                    type="button"
                    disabled
                    aria-label={`Play ${highlight.title} (video unavailable)`}
                    title="Video source not added yet"
                  >
                    <img src="/assets/icons/gallery/play.svg" alt="" />
                  </button>
                </div>
                <div className="gallery-highlight-info">
                  <h3>{highlight.title}</h3>
                  <p>{highlight.duration} · <time dateTime={highlight.dateTime}>{highlight.date}</time></p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
