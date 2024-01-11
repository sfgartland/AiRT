from pathlib import Path
from .price import Price


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
    progress.update(task, completed=len(entries)) #TODO Change to sometging else than len(entries)

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

def genProgressRow(entry):
    inputUrl = entry[0]
    row = [inputUrl]
    if isinstance(entry[1], Path):
        row.append(str(entry[1]))
    else:
        row.append(entry[1])
    return row # TODO If this is still just returning the same we can remove it since it just reproduces the array

def genProgressTable(entries, completed, ignoredEntries=[]) -> Table:
    totalLength = len(entries)
    totalProgress = Progress()
    total_task = totalProgress.add_task("Total progress...", total=totalLength)
    totalProgress.update(total_task, completed=completed) #TODO Change from len(entries) to the real thing


    progressTable = Table(show_footer=True, show_lines=True)
    progressTable.add_column("Video Url", totalProgress)
    progressTable.add_column("Output file")

    for entry in entries:
        row = genProgressRow(entry)
        progressTable.add_row(*row)

    return progressTable
