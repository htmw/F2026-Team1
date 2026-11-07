import { useId, useState } from "react";
import { Search, X } from "lucide-react";
import "../styles/search-bar.css";

function SearchBar({
  id: idProp,
  label = "Search",
  placeholder = "Search…",
  onSearch,
}) {
  const generatedId = useId();
  const id = idProp ?? generatedId;
  const [draft, setDraft] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    onSearch(draft.trim());
  }

  function handleClear() {
    setDraft("");
    onSearch("");
  }

  function handleKeyDown(event) {
    if (event.key === "Escape" && draft) {
      event.preventDefault();
      handleClear();
    }
  }

  return (
    <form className="search-bar" role="search" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor={id}>
        {label}
      </label>

      <Search size={20} className="search-bar__icon" aria-hidden />

      <input
        id={id}
        type="search"
        className="search-bar__control body-md"
        placeholder={placeholder}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        enterKeyHint="search"
        autoComplete="off"
      />

      {draft && (
        <button
          type="button"
          className="search-bar__clear"
          onClick={handleClear}
          aria-label="Clear search"
        >
          <X size={20} aria-hidden />
        </button>
      )}
    </form>
  );
}

export default SearchBar;
