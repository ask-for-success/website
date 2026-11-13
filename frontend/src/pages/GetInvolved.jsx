import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  HeartHandshake,
  UsersRound,
  MessageCircle,
  CalendarDays,
  BriefcaseBusiness,
  GraduationCap,
  Handshake,
  Mail,
} from 'lucide-react';

export default function GetInvolved() {
  return (
    <>
      {/* =====================================
          HERO SECTION
      ===================================== */}

      <section className="involved-hero">
        <div className="container">
          <h1 className="involved-hero-title">
            There's a place for <br />
            <span>you</span> here.
          </h1>

          <div className="involved-hero-layout">
            {/* LEFT CONTENT */}
            <div className="involved-hero-content">
              <p>
                Every success story needs people behind it. Whether you have
                time, resources, or a network to offer, AFS has a way for you to
                help — choose the path that fits you.
              </p>

              <div className="involved-hero-actions">
                <Link to="/get-involved" className="involved-primary-btn">
                  Donate
                </Link>

                <a href="#volunteer" className="involved-outline-btn">
                  Become a volunteer
                  <span>
                    <ArrowRight size={15} />
                  </span>
                </a>
              </div>
            </div>

            {/* RIGHT IMAGE */}
            <div className="involved-hero-image">
              <img
                src="/assets/images/getinvolved/getinvolved1.png"
                alt="Ask For Success community members"
              />
            </div>
          </div>
        </div>
      </section>

      {/* =====================================
          VOLUNTEER SECTION
      ===================================== */}

      <section className="involved-volunteer" id="volunteer">
        <div className="container involved-volunteer-layout">
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
            <h2>Volunteer with us</h2>

            <p className="involved-section-subtitle">
              Give a few hours, change a whole year.
            </p>

            <p className="involved-volunteer-description">
              Volunteers are the heart of every AFS event. You choose how and
              when you help — on the ground, online, or one-to-one with a
              student.
            </p>

            {/* VOLUNTEERING OPPORTUNITIES */}
            <div className="involved-volunteer-list">
              <div className="involved-volunteer-item">
                <span className="involved-list-icon">
                  <CalendarDays size={17} />
                </span>

                <div>
                  <h3>Event support</h3>
                  <p>
                    Welcome students, run logistics and keep our summits
                    flowing.
                  </p>
                </div>
              </div>

              <div className="involved-volunteer-item">
                <span className="involved-list-icon">
                  <GraduationCap size={17} />
                </span>

                <div>
                  <h3>Mentoring</h3>
                  <p>
                    Meet one student once a month to guide their studies or
                    career.
                  </p>
                </div>
              </div>

              <div className="involved-volunteer-item">
                <span className="involved-list-icon">
                  <UsersRound size={17} />
                </span>

                <div>
                  <h3>Workshop facilitation</h3>
                  <p>
                    Lead a session on a skill you know: coding, design, public
                    speaking.
                  </p>
                </div>
              </div>

              <div className="involved-volunteer-item">
                <span className="involved-list-icon">
                  <MessageCircle size={17} />
                </span>

                <div>
                  <h3>Communication</h3>
                  <p>
                    Help us tell the story through photos, videos and social
                    media.
                  </p>
                </div>
              </div>
            </div>

            <Link to="/get-involved" className="involved-primary-btn">
              Apply to volunteer
            </Link>
          </div>
        </div>
      </section>

      {/* =====================================
          PARTNER WITH AFS
      ===================================== */}

      <section className="involved-partner" id="partner">
        <div className="container involved-partner-layout">
          {/* LEFT CONTENT */}
          <div className="involved-partner-content">
            <h2>Partner with AFS</h2>

            <p className="involved-section-subtitle">
              For schools, companies and NGOs.
            </p>

            <p className="involved-partner-description">
              Partners open doors we can't open alone: internships, venues,
              equipment and expertise. We build each partnership around what you
              can offer and what our students need most.
            </p>

            {/* PARTNERSHIP BENEFITS */}
            <div className="involved-partner-benefits">
              <span>
                <UsersRound size={15} />
                Venue & event sponsorship
              </span>

              <span>
                <HeartHandshake size={15} />
                Mentorship & job shadowing
              </span>

              <span>
                <GraduationCap size={15} />
                Workshops in your field
              </span>

              <span>
                <BriefcaseBusiness size={15} />
                Internship support
              </span>
            </div>

            <Link to="/get-involved" className="involved-primary-btn">
              Become a partner
            </Link>
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

      {/* =====================================
    MAKE A DONATION
===================================== */}

      <section className="involved-donation" id="donate">
        <div className="container">
          <div className="involved-donation-header">
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
                className="involved-donation-button"
              >
                Donate cash
              </a>
            </article>

            {/* GOODS DONATION */}
            <article className="involved-donation-card">
              <h3>Give goods</h3>

              <ul>
                <li>Tell us what you'd like to give in a short form.</li>
                <li>
                  We confirm what we can accept and arrange drop-off or pickup.
                </li>
                <li>You receive a confirmation from AFS.</li>
              </ul>

              <a
                href="mailto:askforsuccess@gmail.com?subject=Goods%20donation%20inquiry"
                className="involved-donation-button"
              >
                Donate goods
              </a>
            </article>
          </div>

          {/* CONTACT BANNER */}
          <div className="involved-contact-banner">
            <div className="involved-contact-icon">
              <Mail size={22} />
            </div>

            <p>
              Not sure which path is right for you?{' '}
              <a href="mailto:askforsuccess@gmail.com">Contact us</a> — we're
              happy to help you find the best way to get involved.
            </p>
          </div>
        </div>
      </section>

      {/* =====================================
    FROM SIGN-UP TO FIRST EVENT
===================================== */}

      <section className="involved-steps">
        <div className="container">
          <div className="involved-steps-header">
            <h2>From sign-up to first event</h2>
            <p>Four steps, about two weeks.</p>
          </div>

          <div className="involved-steps-grid">
            <div className="involved-step">
              <div className="involved-step-number">1</div>
              <h3>Apply online</h3>
              <p>Fill in the short form below. It takes about three minutes.</p>
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
                We suggest a role or event that suits your interests and
                schedule.
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
