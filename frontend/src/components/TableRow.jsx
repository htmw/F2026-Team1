import { Link } from "react-router-dom";
import "../styles/table-row.css";

function TableRow({ row, columns, href }) {
  return (
    <div className="table-row" role="row">
      {columns.map((column) => {
        const content = column.render ? column.render(row) : row[column.key];
        const alignClass =
          column.align === "end" ? " table-row__cell--end" : "";
        const extraClass = column.className ? ` ${column.className}` : "";

        return (
          <div
            key={column.key}
            role="cell"
            className={`table-row__cell body-md${alignClass}${extraClass}`}
          >
            {column.isLink && href ? (
              <Link to={href} className="table-row__link">
                {content}
              </Link>
            ) : (
              content
            )}
          </div>
        );
      })}
    </div>
  );
}

export default TableRow;
