import { Routes, Route, Outlet } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Footer from "./components/Footer.jsx";

import Login from "./pages/Login.jsx";
import Home from "./pages/Home.jsx";
import History from "./pages/History.jsx";
import About from "./pages/About.jsx";
import Upload from "./pages/Upload.jsx";
import Results from "./pages/Results.jsx";
import Record from "./pages/Record.jsx";
import Patient from "./pages/Patient.jsx";
import StyleReference from "./pages/StyleReference.jsx";
import RequireAuth from "./components/auth/RequireAuth.jsx";

function AppLayout() {
  return (
    <>
      <Navbar />
      <Outlet />
      <Footer />
    </>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/history" element={<History />} />
          <Route path="/about" element={<About />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/results/:id" element={<Results />} />
          <Route path="/results/:id/record" element={<Record />} />
          <Route path="/patients/:id" element={<Patient />} />
          <Route path="/style" element={<StyleReference />} />
        </Route>
      </Route>
    </Routes>
  );
}

export default App;
