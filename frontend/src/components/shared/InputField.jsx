export default function InputField({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  icon,
  rightElement,
  error,
  onRightElementClick,
  rightElementLabel,
  disabled = false,
  ...rest
}) {
  return (
    <div className="input-field">
      {label && <label>{label}</label>}
      <div className="input-wrapper">
        {icon && <span className="icon-left">{icon}</span>}
        <input
          className={error ? "input-error" : ""}
          type={type}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          {...rest}
        />
        {rightElement && onRightElementClick ? (
          <button
            type="button"
            className="icon-button icon-right"
            onClick={onRightElementClick}
            aria-label={rightElementLabel || "Accion"}
          >
            {rightElement}
          </button>
        ) : (
          rightElement && <span className="icon-right">{rightElement}</span>
        )}
      </div>
      {error && <span className="error-text">{error}</span>}
    </div>
  );
}
