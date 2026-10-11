import TableRow from "./TableRow";
import "../styles/table.css";

function Table({ columns, rows, label, rowKey = "id", rowHref }) {
  const template = columns.map((column) => column.width ?? "1fr").join(" ");

  return (
    <div className="table__wrap">
      <div
        className="table"
        role="table"
        aria-label={label}
        style={{ "--columns": template }}
      >
        <div className="table__head" role="row">
          {columns.map((column) => (
            <div
              key={column.key}
              role="columnheader"
              className={column.hidden ? "sr-only" : "label-mono"}
            >
              {column.label}
            </div>
          ))}
        </div>

        {rows.map((row) => (
          <TableRow
            key={row[rowKey]}
            row={row}
            columns={columns}
            href={rowHref ? rowHref(row) : undefined}
          />
        ))}
      </div>
    </div>
  );
}

export default Table;
