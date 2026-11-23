import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import ArticleCard from '../components/ArticleCard.jsx';
import articles, { articlePath, featuredArticle } from '../data/articles.js';

const categories = ['All', 'Events', 'Student stories', 'Partners', 'Announcements'];

export default function News() {
  const [activeCategory, setActiveCategory] = useState('All');
  const visibleArticles = activeCategory === 'All'
    ? articles
    : articles.filter((article) => article.category === activeCategory);

  return (
    <div className="news-page">
      <section className="news-hero" aria-labelledby="news-page-title">
        <div className="site-shell">
          <header className="listing-intro">
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
                <span>
                  <time dateTime={featuredArticle.dateTime}>{featuredArticle.date}</time>
                  {' · '}{featuredArticle.readTime}
                </span>
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
                <Link className="home-button home-button--large home-button--filled" to={articlePath(featuredArticle)}>
                  Read the story
                </Link>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section className="news-latest-section" id="latest-articles" aria-labelledby="latest-articles-title">
        <div className="site-shell">
          <header className="news-latest-heading">
            <div className="listing-section-title">
              <h2 id="latest-articles-title">Latest articles</h2>
              <p>Recaps, announcements and stories.</p>
            </div>

            <div className="news-category-filters" role="group" aria-label="Filter articles by category">
              {categories.map((category) => (
                <button
                  className="listing-chip news-category-filter"
                  key={category}
                  type="button"
                  aria-pressed={activeCategory === category}
                  onClick={() => setActiveCategory(category)}
                >
                  {category}
                </button>
              ))}
            </div>
          </header>

          <div className="news-article-grid" aria-live="polite">
            {visibleArticles.map((article) => (
              <ArticleCard key={article.slug} article={article} />
            ))}
          </div>

          <div className="news-pagination" role="group" aria-label="News pages">
            <button type="button" className="pagination-arrow" aria-label="Previous page" disabled>
              <img src="/assets/icons/news/previous.svg" alt="" />
            </button>
            <span aria-current="page" aria-label="Page 1">1</span>
            <button type="button" disabled>2</button>
            <button type="button" disabled>3</button>
            <span className="news-pagination-ellipsis" aria-hidden="true">…</span>
            <button type="button" disabled>8</button>
            <button type="button" className="pagination-arrow" aria-label="Next page" disabled>
              <img src="/assets/icons/news/next.svg" alt="" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
