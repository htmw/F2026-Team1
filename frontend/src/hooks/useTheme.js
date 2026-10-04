import { useContext } from "react";
import ThemeContext from "../context/ThemeContext.js";

function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined)
    throw new Error("useTheme was used outside of the ThemeProvider");
  return context;
}

export default useTheme;
