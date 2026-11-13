import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Layout from './components/Layout.jsx';
import Home from './pages/Home.jsx';
import About from './pages/About.jsx';
import GetInvolved from './pages/GetInvolved.jsx';
import Gallery from './pages/Gallery.jsx';
import Events from './pages/Events.jsx';
import News from './pages/News.jsx';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route element={<Layout />}>
                    <Route path="/" element={<Home />} />
                    <Route path="/about" element={<About />} />
                    <Route path="/get-involved" element={<GetInvolved />} />
                    <Route path="/gallery" element={<Gallery />} />
                    <Route path="/events" element={<Events />} />
                    <Route path="/news" element={<News />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}

export default App;