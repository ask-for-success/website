import React from 'react';

const volunteerRoles = [
  {
    title: 'Event support',
    description: 'Welcome students, run logistics and keep our summits flowing.',
  },
  {
    title: 'Mentoring',
    description: 'Meet one student once a month to guide their studies or career.',
  },
  {
    title: 'Workshop facilitation',
    description: 'Lead a session on a skill you know: coding, design, public speaking.',
  },
  {
    title: 'Communication',
    description: 'Help us tell the story through photos, video and social media.',
  },
];

export default function GetInvolved() {
  return (
    <>
      <section className="involved-hero">
        <div className="site-shell involved-hero-layout">
          <div className="involved-hero-content">
            <h1 className="involved-hero-title">There’s a place for you here.</h1>
            <p>
              Every success story needs people behind it. Whether you have
              time, resources, or a network to offer, AFS has a way for you to
              help — choose the path that fits you.
            </p>

            <div className="involved-hero-actions">
              <a href="#donate" className="home-button home-button--large home-button--filled">
                Donate
              </a>
              <a href="#volunteer" className="home-button home-button--large home-button--outline">
                Become a volunteer
                <img src="/assets/icons/home/arrow-outlined.svg" alt="" />
              </a>
            </div>
          </div>

          <div className="involved-hero-image">
            <img
              src="/assets/images/getinvolved/getinvolved1.png"
              alt="Ask For Success community members"
              fetchPriority="high"
            />
          </div>
        </div>
      </section>
      <section className="involved-volunteer" id="volunteer" tabIndex={-1}>
        <div className="site-shell involved-volunteer-layout">
          {/* LEFT IMAGE */}
          <div className="involved-volunteer-image">
            <img
              src="/assets/images/getinvolved/getinvolved2.jpg"
              alt="AFS volunteer participating in an event"
              loading="lazy"
            />
          </div>

          {/* RIGHT CONTENT */}
          <div className="involved-volunteer-content">
            <div className="involved-section-heading">
              <h2>Volunteer with us</h2>
              <p>Give a few hours, change a whole year.</p>
            </div>

            <p className="involved-volunteer-description">
              Volunteers are the heart of every AFS event. You choose how and
              when you help — on the ground, online, or one-to-one with a
              student.
            </p>

            {/* VOLUNTEERING OPPORTUNITIES */}
            <div className="involved-volunteer-list">
              {volunteerRoles.map(({ title, description }) => (
                <div className="involved-volunteer-item" key={title}>
                  <span className="involved-list-icon">
                    <img src="/assets/icons/get-involved/volunteer-check.svg" alt="" />
                  </span>
                  <div>
                    <h3>{title}</h3>
                    <p>{description}</p>
                  </div>
                </div>
              ))}
            </div>

            <a href="mailto:askforsuccess@gmail.com?subject=Volunteering%20inquiry" className="home-button home-button--large home-button--filled">
              Ask about volunteering
            </a>
          </div>
        </div>
      </section>
      <section className="involved-partner" id="partner" tabIndex={-1}>
        <div className="site-shell involved-partner-layout">
          {/* LEFT CONTENT */}
          <div className="involved-partner-content">
            <div className="involved-section-heading">
              <h2>Partner with AFS</h2>
              <p>For schools, companies and NGOs.</p>
            </div>

            <p className="involved-partner-description">
              Partners open doors we can’t open alone: internships, venues,
              equipment and expertise. We build each partnership around what you
              can offer and what our students need most.
            </p>

            {/* PARTNERSHIP BENEFITS */}
            <div className="involved-partner-benefits">
              <span className="home-about-feature">
                <img src="/assets/icons/home/community.svg" alt="" />
                Venues &amp; event sponsorship
              </span>
              <span className="home-about-feature">
                <img src="/assets/icons/home/opportunity.svg" alt="" />
                Internships &amp; job shadowing
              </span>
              <span className="home-about-feature">
                <img src="/assets/icons/home/education.svg" alt="" />
                Workshops in your field
              </span>
              <span className="home-about-feature">
                <img src="/assets/icons/home/impact.svg" alt="" />
                Yearly impact report
              </span>
            </div>

            <a href="mailto:askforsuccess@gmail.com?subject=Partnership%20inquiry" className="home-button home-button--large home-button--filled">
              Ask about partnering
            </a>
          </div>

          {/* RIGHT IMAGE */}
          <div className="involved-partner-image">
            <img
              src="/assets/images/getinvolved/getinvolved3.jpg"
              alt="AFS students and partners at a community event"
              loading="lazy"
            />
          </div>
        </div>
      </section>
      <section className="involved-donation" id="donate" tabIndex={-1}>
        <div className="site-shell involved-donation-layout">
          <div className="involved-section-heading">
            <h2>Make a donation</h2>
            <p>Every dirham goes to a student programme.</p>
          </div>

          <div className="involved-donation-grid">
            {/* CASH DONATION */}
            <article className="involved-donation-card">
              <h3>Give cash</h3>

              <ul>
                <li>Fill in a short form with your details.</li>
                <li>We contact you with the donation instructions.</li>
                <li>You receive a confirmation from AFS.</li>
              </ul>

              <a
                href="mailto:askforsuccess@gmail.com?subject=Cash%20donation%20inquiry"
                className="home-button home-button--filled involved-donation-button"
              >
                Donate cash
              </a>
            </article>

            {/* GOODS DONATION */}
            <article className="involved-donation-card">
              <h3>Give goods</h3>

              <ul>
                <li>Tell us what you’d like to give in a short form.</li>
                <li>
                  We confirm what we can accept and arrange drop-off or pickup.
                </li>
                <li>You receive a confirmation from AFS.</li>
              </ul>

              <a
                href="mailto:askforsuccess@gmail.com?subject=Goods%20donation%20inquiry"
                className="home-button home-button--filled involved-donation-button"
              >
                Donate goods
              </a>
            </article>
          </div>

          {/* CONTACT BANNER */}
          <div className="involved-contact-banner">
            <div className="involved-contact-icon">
              <img src="/assets/icons/get-involved/mail.svg" alt="" />
            </div>

            <p>
              Not sure which path is right for you?{' '}
              <a href="mailto:askforsuccess@gmail.com">Contact us</a> — we’re
              happy to help you find the best way to get involved.
            </p>
          </div>
        </div>
      </section>
      <section className="involved-steps">
        <div className="site-shell involved-steps-layout">
          <div className="involved-section-heading">
            <h2>From sign-up to first event</h2>
            <p>Four steps, about two weeks.</p>
          </div>

          <div className="involved-steps-grid">
            <div className="involved-step">
              <div className="involved-step-number">1</div>
              <h3>Get in touch</h3>
              <p>Email us to express interest in volunteering.</p>
            </div>

            <div className="involved-step">
              <div className="involved-step-number">2</div>
              <h3>Meet the team</h3>
              <p>
                We call you within a week to understand your skills and
                availability.
              </p>
            </div>

            <div className="involved-step">
              <div className="involved-step-number">3</div>
              <h3>Get matched</h3>
              <p>
                We suggest a role, an event or a student that fits what you offer.
              </p>
            </div>

            <div className="involved-step">
              <div className="involved-step-number">4</div>
              <h3>Start helping</h3>
              <p>
                Join your first activity with an experienced member by your
                side.
              </p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
