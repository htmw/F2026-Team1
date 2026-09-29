import { Routes, Route } from "react-router-dom";
import StyleReference from "./pages/StyleReference.jsx";
import Home from "./pages/Home.jsx";

function App() {
  return (
    <Routes>
      <Route path="/style" element={<StyleReference />} />
      <Route path="/" element={<Home />} />
    </Routes>
  );
}

export default App;
