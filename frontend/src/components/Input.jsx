import { useId, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import "../styles/input.css";

function Input({
  id: idProp,
  label,
  hint,
  error,
  icon: Icon,
  type = "text",
  hideLabel = false,
  ...rest
}) {
  const generatedId = useId();
  const id = idProp ?? generatedId;
  const messageId = `${id}-message`;
  const [isRevealed, setIsRevealed] = useState(false);

  const isPassword = type === "password";
  const inputType = isPassword && isRevealed ? "text" : type;
  const message = error ?? hint;

  const controlClass = [
    "input__control",
    "body-md",
    Icon && "input__control--with-icon",
    isPassword && "input__control--with-action",
    error && "input__control--error",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="input">
      <label
        className={`input__label body-md${hideLabel ? " sr-only" : ""}`}
        htmlFor={id}
      >
        {label}
      </label>

      <div className="input__field">
        {Icon && <Icon size={20} className="input__icon" aria-hidden />}

        <input
          id={id}
          type={inputType}
          className={controlClass}
          aria-invalid={error ? true : undefined}
          aria-describedby={message ? messageId : undefined}
          {...rest}
        />

        {isPassword && (
          <button
            type="button"
            className="input__action"
            onClick={() => setIsRevealed((prev) => !prev)}
            aria-label={isRevealed ? "Hide password" : "Show password"}
            aria-pressed={isRevealed}
          >
            {isRevealed ? (
              <EyeOff size={20} aria-hidden />
            ) : (
              <Eye size={20} aria-hidden />
            )}
          </button>
        )}
      </div>

      {message && (
        <p
          id={messageId}
          className={`input__message caption-rg${error ? " input__message--error" : ""}`}
        >
          {message}
        </p>
      )}
    </div>
  );
}

export default Input;
