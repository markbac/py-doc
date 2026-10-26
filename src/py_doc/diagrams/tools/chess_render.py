"""Draw a chessboard with python-chess, from the JSON py-doc wrote from a ``chess`` fence.

    python3 chess_render.py <board.json> <board.svg>

python-chess is GPL-3.0. It runs here, in the tool image, as a program of its own; py-doc does not import it.
"""

import json
import sys

import chess
import chess.svg


def main(source, output):
    with open(source, encoding="utf-8") as f:
        spec = json.load(f)
    try:
        board = chess.Board(spec["fen"])
    except ValueError as exc:
        sys.exit(f"the fen is not a position: {exc}")
    fill = {chess.parse_square(square): "#f2c27a" for square in spec["highlight"]}
    arrows = [
        chess.svg.Arrow(chess.parse_square(a["from"]), chess.parse_square(a["to"]), color=a["colour"])
        for a in spec["arrows"]
    ]
    picture = chess.svg.board(board, fill=fill, arrows=arrows, flipped=spec["flip"], size=400)
    with open(output, "w", encoding="utf-8") as f:
        f.write(picture)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
