import useTheme from "../hooks/useTheme.js";

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button className="btn-primary" onClick={toggleTheme}>
      {theme === "dark" ? "Light Mode" : "Dark Mode"}
    </button>
  );
}

export default ThemeToggle;
