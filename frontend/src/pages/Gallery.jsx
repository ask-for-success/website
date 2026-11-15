
import React, { useState } from 'react';
import { ArrowRight, Play } from 'lucide-react';
const categories = [
  'All',
  'Summits',
  'Workshops',
  'Outreach',
  'Community',
  'Behind the scenes'
];
const photos = [
  {
    id: 1,
    image: '/assets/images/gallery/Youth Summit 2026.png',
    title: 'Youth Summit 2026',
    category: 'Summits'
  },
  {
    id: 2,
    image: '/assets/images/gallery/Atlas outreach day.jpg',
    title: 'Atlas outreach day',
    category: 'Outreach'
  },
  {
    id: 3,
    image: '/assets/images/gallery/Opening day.png',
    title: 'Opening day',
    category: 'Community'
  },
  {
    id: 4,
    image: '/assets/images/gallery/Flag ceremony, Ain Chok.jpg',
    title: 'Flag ceremony, Ain Chok',
    category: 'Community'
  },
  {
    id: 5,
    image: '/assets/images/gallery/Lycée workshop, Casablanca.png',
    title: 'Lycée workshop, Casablanca',
    category: 'Workshops'
  },
  {
    id: 6,
    image: '/assets/images/gallery/children2.jpg',
    category: 'Outreach'
  },
  {
    id: 7,
    image: '/assets/images/gallery/Volunteer team.jpg',
    title: 'Volunteer team',
    category: 'Behind the scenes'
  },
  {
    id: 8,
    image: '/assets/images/gallery/children1.jpg',
    category: 'Community'
  },
  {
    id: 9,
    image: '/assets/images/gallery/Graduation 2025.jpg',
    title: 'Graduation 2025',
    category: 'Community'
  }
];

const highlights = [
  {
    id: 'youth-summit-aftermovie',
    image: '/assets/images/gallery/vedio1.png',
    title: 'Youth Summit 2026 — aftermovie',
    duration: '3 min',
    date: 'October 2026',
    dateTime: '2026-10'
  },
  {
    id: 'atlas-day',
    image: '/assets/images/gallery/vedio2.jpg',
    title: 'A day in the Atlas with AFS',
    duration: '5 min',
    date: 'June 2026',
    dateTime: '2026-06'
  }
];

const INITIAL_COUNT = 9;
const LOAD_COUNT = 6;
export default function Gallery() {
  const [activeCategory, setActiveCategory] = useState('All');
  const [visibleCount, setVisibleCount] = useState(INITIAL_COUNT);

  const filteredPhotos =
    activeCategory === 'All'
      ? photos
      : photos.filter(
          (photo) => photo.category === activeCategory
        );

  const visiblePhotos = filteredPhotos.slice(0, visibleCount);

  function changeCategory(category) {
    setActiveCategory(category);
    setVisibleCount(INITIAL_COUNT);
  }

  const columns = [[], [], []];

  visiblePhotos.forEach((photo, index) => {
    columns[index % 3].push(photo);
  });

  return (
    <>
      <section className="gallery-hero">
        <div className="container gallery-hero-layout">

          <div className="gallery-hero-heading">
            <h1>
              Moments that <br />
              tell our <span>story.</span>
            </h1>
          </div>

          <div className="gallery-hero-description">
            <p>
              Summits, workshops and outreach days
              across Morocco, captured by our
              volunteers and the students themselves.
            </p>
          </div>

        </div>
      </section>
      <section className="gallery-content">
        <div className="container">

          {/* CATEGORY FILTERS */}
          <div
            className="gallery-filters"
            aria-label="Gallery filters"
          >
            {categories.map((category) => (
              <button
                key={category}
                type="button"
                className={
                  activeCategory === category
                    ? 'gallery-filter active'
                    : 'gallery-filter'
                }
                onClick={() => changeCategory(category)}
                aria-pressed={activeCategory === category}
              >
                {category}
              </button>
            ))}
          </div>

          {/* THREE INDEPENDENT COLUMNS */}
          <div className="afs-gallery-grid">

            {columns.map((column, columnIndex) => (
              <div
                className="afs-gallery-column"
                key={columnIndex}
              >

                {column.map((photo) => (
                  <figure
                    className="afs-gallery-item"
                    key={photo.id}
                  >

                    <img
                      src={photo.image}
                      alt={
                        photo.title ||
                        `${photo.category} activity`
                      }
                      loading="lazy"
                    />

                    {/* CAPTION ONLY IF TITLE EXISTS */}
                    {photo.title && (
                      <figcaption className="afs-gallery-caption">
                        {photo.title}
                      </figcaption>
                    )}

                  </figure>
                ))}

              </div>
            ))}

          </div>

          {/* EMPTY STATE */}
          {filteredPhotos.length === 0 && (
            <p className="gallery-empty">
              No photos available in this category yet.
            </p>
          )}

          {/* LOAD MORE */}
          {filteredPhotos.length > 0 && (
            <div className="gallery-load-more">
              <button
                type="button"
                className="gallery-load-button"
                disabled={visibleCount >= filteredPhotos.length}
                onClick={() =>
                  setVisibleCount(
                    (count) => Math.min(
                      count + LOAD_COUNT,
                      filteredPhotos.length
                    )
                  )
                }
              >
                Load more photos

                <span aria-hidden="true">
                  <ArrowRight size={12} />
                </span>
              </button>
            </div>
          )}

        </div>
      </section>

      <section className="gallery-highlights">
        <div className="container gallery-highlights-container">
          <header className="gallery-highlights-heading">
            <h2>Watch the highlights</h2>
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
                    aria-label={`Play ${highlight.title}; video source not added yet`}
                    title="Video source not added yet"
                  >
                    <Play size={18} fill="currentColor" aria-hidden="true" />
                  </button>
                </div>

                <h3>{highlight.title}</h3>
                <p className="gallery-highlight-meta">
                  <span>{highlight.duration}</span>
                  <span aria-hidden="true">·</span>
                  <time dateTime={highlight.dateTime}>{highlight.date}</time>
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
