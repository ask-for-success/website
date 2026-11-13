import React from 'react';
import EventCard from '../components/EventCard.jsx';
import SectionTitle from '../components/SectionTitle.jsx';
import events from '../data/events.js';

export default function Events() {
  return (
    <section className="section container page-section">
      <SectionTitle
        eyebrow="Events"
        title="Good things happen when we gather"
        description="Join us to meet people, share ideas, and make community connections."
      />
      <div className="card-grid">
        {events.map((event) => <EventCard key={event.id} event={event} />)}
      </div>
    </section>
  );
}
