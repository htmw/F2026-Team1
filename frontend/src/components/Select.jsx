import { ChevronDown } from "lucide-react";
import "../styles/select.css";

function Select({ options, placeholder, ...rest }) {
  return (
    <div className="select">
      <select className="select__control body-md" {...rest}>
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown size={20} className="select__chevron" aria-hidden />
    </div>
  );
}

export default Select;
