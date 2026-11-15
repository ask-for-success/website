import React, { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ArticleCard from '../components/ArticleCard.jsx';
import articles, { featuredArticle } from '../data/articles.js';

const categories = [
  { label: 'All', value: 'All' },
  { label: 'Events', value: 'Events' },
  { label: 'Student stories', value: 'Student stories' },
  { label: 'Parters', value: 'Partners' },
  { label: 'Announcements', value: 'Announcements' },
];

export default function News() {
  const [activeCategory, setActiveCategory] = useState('All');
  const visibleArticles = useMemo(
    () => activeCategory === 'All'
      ? articles
      : articles.filter((article) => article.category === activeCategory),
    [activeCategory],
  );

  return (
    <div className="news-page">
      <section className="news-hero" aria-labelledby="news-page-title">
        <div className="container news-hero-inner">
          <header className="news-page-heading">
            <h1 id="news-page-title">
              News &amp; <span>stories</span>
            </h1>
            <p>
              What’s new at AFS: event recaps, student journeys and the people
              who make it happen.
            </p>
          </header>

          <article className="news-featured-story" id="featured-story">
            <div className="news-featured-image">
              <img
                src={featuredArticle.image}
                alt={featuredArticle.imageAlt}
                fetchPriority="high"
              />
            </div>

            <div className="news-featured-content">
              <div className="news-featured-meta">
                <span className="news-featured-category">{featuredArticle.category}</span>
                <time dateTime={featuredArticle.dateTime}>{featuredArticle.date}</time>
                <span aria-hidden="true">·</span>
                <span>{featuredArticle.readTime}</span>
              </div>
              <h2>{featuredArticle.title}</h2>
              <p className="news-featured-excerpt">{featuredArticle.excerpt}</p>

              <div className="news-featured-bottom">
                <div className="news-byline">
                  <img src={featuredArticle.authorImage} alt="" />
                  <span>
                    <strong>{featuredArticle.author}</strong>
                    <small>{featuredArticle.authorRole}</small>
                  </span>
                </div>
                <a className="news-featured-link" href="#latest-articles">
                  Read the story
                </a>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section className="news-latest-section" id="latest-articles" aria-labelledby="latest-articles-title">
        <div className="container">
          <header className="news-latest-heading">
            <div>
              <h2 id="latest-articles-title">Latest articles</h2>
              <p>Recaps, announcements and stories.</p>
            </div>

            <div className="news-category-filters" role="group" aria-label="Filter articles by category">
              {categories.map(({ label, value }) => (
                <button
                  className={activeCategory === value ? 'news-category-filter active' : 'news-category-filter'}
                  key={value}
                  type="button"
                  aria-pressed={activeCategory === value}
                  onClick={() => setActiveCategory(value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </header>

          <div className="news-article-grid" aria-live="polite">
            {visibleArticles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>

          <nav className="news-pagination" aria-label="News pages">
            <button type="button" className="pagination-arrow" aria-label="Previous page" disabled>
              <ChevronLeft size={12} aria-hidden="true" />
            </button>
            <button type="button" className="active" aria-current="page">1</button>
            <button type="button" disabled>2</button>
            <button type="button" disabled>3</button>
            <span aria-hidden="true">…</span>
            <button type="button" disabled>8</button>
            <button type="button" className="pagination-arrow" aria-label="Next page" disabled>
              <ChevronRight size={12} aria-hidden="true" />
            </button>
          </nav>
        </div>
      </section>
    </div>
  );
}
