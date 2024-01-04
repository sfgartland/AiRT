from .AI_research_tools.price import Price


from rich.table import Table
from rich.progress import Progress


def genPriceRow(entry, hideInputPrice, hideOutputPrice):
    inputFile = entry[0][0]
    row = [inputFile.as_posix()]
    if entry[1]:
        cost = entry[1]
        row.append(f"[b]{Price.readablePrice(cost.totalPrice)}[/b]")
        if not hideInputPrice:
            row.append(Price.readablePrice(cost.inputPrice))
        if not hideOutputPrice:
            row.append(Price.readablePrice(cost.outputPrice))
    else:
        row.append("...")
        if not hideInputPrice:
            row.append("...")
        if not hideOutputPrice:
            row.append("...")

    return row


def genPriceTable(
    entries, ignoredEntries=[], hideInputPrice=False, hideOutputPrice=False
) -> Table:
    totalLength = len(entries)
    totalPrice = Price.sumPrices([entry[1] for entry in entries if entry[1]])

    progress = Progress()
    task = progress.add_task("Estimating costs...", total=totalLength)
    progress.update(task, completed=len(entries))

    priceTable = Table(show_footer=True)
    # priceTable.add_column(None, len(entries))
    priceTable.add_column(f"File (count: {totalLength})", progress)
    priceTable.add_column(
        "Total Price", "[green]" + Price.readablePrice(totalPrice.totalPrice)
    )
    if not hideInputPrice:
        priceTable.add_column("Input Price", Price.readablePrice(totalPrice.inputPrice))
    if not hideOutputPrice:
        priceTable.add_column(
            "Output Price", Price.readablePrice(totalPrice.outputPrice)
        )

    for entry in entries:
        row = genPriceRow(entry, hideInputPrice, hideOutputPrice)
        priceTable.add_row(*row)

    # if len(ignoredEntries) > 0:
    #     priceTable.add_section()
    #     for entry in ignoredEntries:
    #         row = genPriceRow(entry, hideInputPrice, hideOutputPrice)
    #         priceTable.add_row(*row)

    return priceTable
