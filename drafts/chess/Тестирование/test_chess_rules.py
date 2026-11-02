#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proverka generatora hodov. Ta zhe model, chto v module formy Shahmaty."""

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
KIWI = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"


def new_pos():
    return {
        "board": [0] * 64,
        "side": 1,
        "wk": False,
        "wq": False,
        "bk": False,
        "bq": False,
        "ep": -1,
        "half": 0,
        "full": 1,
    }


def file_of(sq):
    return sq % 8


def rank_of(sq):
    return sq // 8


def sq_of(file, rank):
    return file + rank * 8


def parse_sq(name):
    if not name or name == "-" or len(name) < 2:
        return -1
    file = ord(name[0]) - ord("a")
    rank = ord(name[1]) - ord("1")
    if file < 0 or file > 7 or rank < 0 or rank > 7:
        return -1
    return sq_of(file, rank)


def name_of(sq):
    return chr(ord("a") + file_of(sq)) + chr(ord("1") + rank_of(sq))


def piece_from_char(ch):
    table = {"P": 1, "N": 2, "B": 3, "R": 4, "Q": 5, "K": 6,
             "p": -1, "n": -2, "b": -3, "r": -4, "q": -5, "k": -6}
    return table[ch]


def char_from_piece(piece):
    table = {1: "P", 2: "N", 3: "B", 4: "R", 5: "Q", 6: "K"}
    ch = table[abs(piece)]
    return ch if piece > 0 else ch.lower()


def parse_fen(fen):
    pos = new_pos()
    parts = fen.split(" ")
    ranks = parts[0].split("/")
    base = 56
    for rank_text in ranks:
        cursor = base
        for ch in rank_text:
            if ch.isdigit():
                cursor += int(ch)
            else:
                pos["board"][cursor] = piece_from_char(ch)
                cursor += 1
        base -= 8
    pos["side"] = -1 if parts[1] == "b" else 1
    rights = parts[2]
    pos["wk"] = "K" in rights
    pos["wq"] = "Q" in rights
    pos["bk"] = "k" in rights
    pos["bq"] = "q" in rights
    pos["ep"] = parse_sq(parts[3])
    pos["half"] = int(parts[4])
    pos["full"] = int(parts[5])
    return pos


def write_fen(pos):
    rows = []
    for index in range(8):
        rank = 7 - index
        empty = 0
        text = ""
        for file in range(8):
            piece = pos["board"][sq_of(file, rank)]
            if piece == 0:
                empty += 1
            else:
                if empty:
                    text += str(empty)
                    empty = 0
                text += char_from_piece(piece)
        if empty:
            text += str(empty)
        rows.append(text)
    rights = ""
    if pos["wk"]:
        rights += "K"
    if pos["wq"]:
        rights += "Q"
    if pos["bk"]:
        rights += "k"
    if pos["bq"]:
        rights += "q"
    if not rights:
        rights = "-"
    ep = "-" if pos["ep"] < 0 else name_of(pos["ep"])
    side = "w" if pos["side"] > 0 else "b"
    return "%s %s %s %s %s %s" % ("/".join(rows), side, rights, ep, pos["half"], pos["full"])


def pack(src, dst, promo=0, castle=0, ep=0):
    return src + dst * 64 + promo * 4096 + castle * 32768 + ep * 131072


def src_of(move):
    return move % 64


def dst_of(move):
    return (move // 64) % 64


def promo_of(move):
    return (move // 4096) % 8


def castle_of(move):
    return (move // 32768) % 4


def ep_of(move):
    return (move // 131072) % 2


def same_side(piece, side):
    if piece == 0:
        return False
    return (piece > 0 and side > 0) or (piece < 0 and side < 0)


def contains(board, file, rank, code):
    if file < 0 or file > 7 or rank < 0 or rank > 7:
        return False
    return board[sq_of(file, rank)] == code


def ray_hits(board, file, rank, df, dr, first, second):
    file += df
    rank += dr
    while 0 <= file <= 7 and 0 <= rank <= 7:
        piece = board[sq_of(file, rank)]
        if piece != 0:
            return piece == first or piece == second
        file += df
        rank += dr
    return False


def knight_hits(board, file, rank, code):
    deltas = ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))
    return any(contains(board, file + df, rank + dr, code) for df, dr in deltas)


def king_hits(board, file, rank, code):
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if df == 0 and dr == 0:
                continue
            if contains(board, file + df, rank + dr, code):
                return True
    return False


def attacked(board, sq, by_side):
    if sq < 0:
        return False
    file = file_of(sq)
    rank = rank_of(sq)
    pawn_rank = rank - by_side
    pawn = by_side
    if 0 <= pawn_rank <= 7:
        if file > 0 and board[sq_of(file - 1, pawn_rank)] == pawn:
            return True
        if file < 7 and board[sq_of(file + 1, pawn_rank)] == pawn:
            return True
    if knight_hits(board, file, rank, 2 * by_side):
        return True
    if king_hits(board, file, rank, 6 * by_side):
        return True
    rook = 4 * by_side
    bishop = 3 * by_side
    queen = 5 * by_side
    rays = ((1, 0, rook), (-1, 0, rook), (0, 1, rook), (0, -1, rook),
            (1, 1, bishop), (1, -1, bishop), (-1, 1, bishop), (-1, -1, bishop))
    for df, dr, slider in rays:
        if ray_hits(board, file, rank, df, dr, slider, queen):
            return True
    return False


def find_king(board, side):
    code = 6 * side
    for sq in range(64):
        if board[sq] == code:
            return sq
    return -1


def add_step(pos, moves, src, df, dr, side):
    file = file_of(src) + df
    rank = rank_of(src) + dr
    if file < 0 or file > 7 or rank < 0 or rank > 7:
        return
    dst = sq_of(file, rank)
    target = pos["board"][dst]
    if target == 0 or not same_side(target, side):
        moves.append(pack(src, dst))


def add_ray(pos, moves, src, df, dr, side):
    file = file_of(src) + df
    rank = rank_of(src) + dr
    while 0 <= file <= 7 and 0 <= rank <= 7:
        dst = sq_of(file, rank)
        target = pos["board"][dst]
        if target == 0:
            moves.append(pack(src, dst))
        else:
            if not same_side(target, side):
                moves.append(pack(src, dst))
            return
        file += df
        rank += dr


def add_pawn_move(moves, src, dst, promote):
    if promote:
        for promo in (5, 4, 3, 2):
            moves.append(pack(src, dst, promo))
    else:
        moves.append(pack(src, dst))


def add_pawns(pos, moves, src):
    board = pos["board"]
    side = pos["side"]
    file = file_of(src)
    rank = rank_of(src)
    start = 1 if side > 0 else 6
    last = 7 if side > 0 else 0
    new_rank = rank + side
    if new_rank < 0 or new_rank > 7:
        return
    dst = sq_of(file, new_rank)
    if board[dst] == 0:
        add_pawn_move(moves, src, dst, new_rank == last)
        if rank == start:
            double = sq_of(file, rank + 2 * side)
            if board[double] == 0:
                moves.append(pack(src, double))
    for df in (-1, 1):
        new_file = file + df
        if new_file < 0 or new_file > 7:
            continue
        cap = sq_of(new_file, new_rank)
        target = board[cap]
        if target != 0 and not same_side(target, side):
            add_pawn_move(moves, src, cap, new_rank == last)
        elif cap == pos["ep"]:
            moves.append(pack(src, cap, 0, 0, 1))


def add_castles(pos, moves):
    board = pos["board"]
    side = pos["side"]
    if side > 0:
        if pos["wk"] and board[4] == 6 and board[7] == 4 and board[5] == 0 and board[6] == 0:
            if not attacked(board, 4, -1) and not attacked(board, 5, -1) and not attacked(board, 6, -1):
                moves.append(pack(4, 6, 0, 1, 0))
        if pos["wq"] and board[4] == 6 and board[0] == 4 and board[1] == 0 and board[2] == 0 and board[3] == 0:
            if not attacked(board, 4, -1) and not attacked(board, 3, -1) and not attacked(board, 2, -1):
                moves.append(pack(4, 2, 0, 2, 0))
    else:
        if pos["bk"] and board[60] == -6 and board[63] == -4 and board[61] == 0 and board[62] == 0:
            if not attacked(board, 60, 1) and not attacked(board, 61, 1) and not attacked(board, 62, 1):
                moves.append(pack(60, 62, 0, 1, 0))
        if pos["bq"] and board[60] == -6 and board[56] == -4 and board[57] == 0 and board[58] == 0 and board[59] == 0:
            if not attacked(board, 60, 1) and not attacked(board, 59, 1) and not attacked(board, 58, 1):
                moves.append(pack(60, 58, 0, 2, 0))


def pseudo(pos):
    moves = []
    side = pos["side"]
    for sq in range(64):
        piece = pos["board"][sq]
        if not same_side(piece, side):
            continue
        kind = abs(piece)
        if kind == 1:
            add_pawns(pos, moves, sq)
        elif kind == 2:
            for df, dr in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)):
                add_step(pos, moves, sq, df, dr, side)
        elif kind == 3:
            for df, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                add_ray(pos, moves, sq, df, dr, side)
        elif kind == 4:
            for df, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                add_ray(pos, moves, sq, df, dr, side)
        elif kind == 5:
            for df, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                add_ray(pos, moves, sq, df, dr, side)
        elif kind == 6:
            for df in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    if df or dr:
                        add_step(pos, moves, sq, df, dr, side)
    add_castles(pos, moves)
    return moves


def make(pos, move):
    board = pos["board"]
    src = src_of(move)
    dst = dst_of(move)
    promo = promo_of(move)
    castle = castle_of(move)
    is_ep = ep_of(move)
    piece = board[src]
    captured = board[dst]
    victim = -1
    rook_from = -1
    rook_to = -1
    rook_piece = 0
    if is_ep:
        victim = dst - 8 if piece > 0 else dst + 8
        captured = board[victim]
        board[victim] = 0
    if castle == 1:
        if piece > 0:
            rook_from, rook_to = 7, 5
        else:
            rook_from, rook_to = 63, 61
    elif castle == 2:
        if piece > 0:
            rook_from, rook_to = 0, 3
        else:
            rook_from, rook_to = 56, 59
    if rook_from >= 0:
        rook_piece = board[rook_from]
        board[rook_to] = rook_piece
        board[rook_from] = 0
    board[src] = 0
    if promo:
        board[dst] = promo if piece > 0 else -promo
    else:
        board[dst] = piece
    undo = {
        "src": src, "dst": dst, "piece": piece, "captured": captured, "epflag": is_ep,
        "victim": victim, "rook_from": rook_from, "rook_to": rook_to, "rook_piece": rook_piece,
        "wk": pos["wk"], "wq": pos["wq"], "bk": pos["bk"], "bq": pos["bq"],
        "ep": pos["ep"], "side": pos["side"], "half": pos["half"], "full": pos["full"],
    }
    drop_rights(pos, src, dst, piece)
    kind = abs(piece)
    if kind == 1 and abs(dst - src) == 16:
        pos["ep"] = src + 8 if dst > src else src - 8
    else:
        pos["ep"] = -1
    if kind == 1 or captured != 0:
        pos["half"] = 0
    else:
        pos["half"] += 1
    if pos["side"] < 0:
        pos["full"] += 1
    pos["side"] = -pos["side"]
    return undo


def drop_rights(pos, src, dst, piece):
    if piece == 6 or src == 4:
        pos["wk"] = False
        pos["wq"] = False
    if piece == -6 or src == 60:
        pos["bk"] = False
        pos["bq"] = False
    if src == 7 or dst == 7:
        pos["wk"] = False
    if src == 0 or dst == 0:
        pos["wq"] = False
    if src == 63 or dst == 63:
        pos["bk"] = False
    if src == 56 or dst == 56:
        pos["bq"] = False


def unmake(pos, undo):
    board = pos["board"]
    if undo["epflag"]:
        board[undo["dst"]] = 0
        board[undo["victim"]] = undo["captured"]
    else:
        board[undo["dst"]] = undo["captured"]
    board[undo["src"]] = undo["piece"]
    if undo["rook_from"] >= 0:
        board[undo["rook_to"]] = 0
        board[undo["rook_from"]] = undo["rook_piece"]
    pos["wk"] = undo["wk"]
    pos["wq"] = undo["wq"]
    pos["bk"] = undo["bk"]
    pos["bq"] = undo["bq"]
    pos["ep"] = undo["ep"]
    pos["side"] = undo["side"]
    pos["half"] = undo["half"]
    pos["full"] = undo["full"]


def legal(pos):
    result = []
    mover = pos["side"]
    for move in pseudo(pos):
        undo = make(pos, move)
        king = find_king(pos["board"], mover)
        if king >= 0 and not attacked(pos["board"], king, pos["side"]):
            result.append(move)
        unmake(pos, undo)
    return result


def perft(pos, depth):
    if depth == 0:
        return 1
    total = 0
    for move in legal(pos):
        undo = make(pos, move)
        total += perft(pos, depth - 1)
        unmake(pos, undo)
    return total


def find_move(pos, src_name, dst_name, promo=0):
    src = parse_sq(src_name)
    dst = parse_sq(dst_name)
    for move in legal(pos):
        if src_of(move) == src and dst_of(move) == dst and (promo == 0 or promo_of(move) == promo):
            return move
    return -1


def play(pos, src_name, dst_name, promo=0):
    move = find_move(pos, src_name, dst_name, promo)
    if move < 0:
        raise AssertionError("illegal %s-%s" % (src_name, dst_name))
    make(pos, move)
    return move


def main():
    errors = []

    def check(name, condition):
        if condition:
            print("OK " + name)
        else:
            errors.append(name)
            print("FAIL " + name)

    start = parse_fen(START)
    check("fen roundtrip", write_fen(start) == START)
    check("perft1", perft(start, 1) == 20)
    check("perft2", perft(start, 2) == 400)
    check("perft3", perft(start, 3) == 8902)
    kiwi = parse_fen(KIWI)
    check("kiwi fen", write_fen(kiwi) == KIWI)
    check("kiwi1", perft(kiwi, 1) == 48)
    check("kiwi2", perft(kiwi, 2) == 2039)

    game = parse_fen(START)
    play(game, "e2", "e4")
    play(game, "e7", "e5")
    play(game, "d1", "h5")
    play(game, "b8", "c6")
    play(game, "f1", "c4")
    play(game, "g8", "f6")
    play(game, "h5", "f7")
    check("scholar mate no moves", len(legal(game)) == 0)
    king = find_king(game["board"], game["side"])
    check("scholar is check", attacked(game["board"], king, -game["side"]))

    ep = parse_fen("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3")
    ep_move = find_move(ep, "e5", "d6")
    check("en passant exists", ep_move >= 0 and ep_of(ep_move) == 1)
    make(ep, ep_move)
    check("en passant captured pawn", ep["board"][parse_sq("d5")] == 0 and ep["board"][parse_sq("d6")] == 1)

    pin = parse_fen("4r3/8/8/8/8/8/4N3/4K3 w - - 0 1")
    knight_moves = [mv for mv in legal(pin) if src_of(mv) == parse_sq("e2")]
    check("pinned knight stays", len(knight_moves) == 0)
    check("king escapes pin", find_move(pin, "e1", "d1") >= 0 or find_move(pin, "e1", "f1") >= 0)

    checked = parse_fen("4k3/8/8/8/8/8/8/R3K2q w Q - 0 1")
    check("no castle in check", find_move(checked, "e1", "c1") < 0)

    castle = parse_fen("4k3/8/8/8/8/8/8/R3K3 w Q - 0 1")
    castle_move = find_move(castle, "e1", "c1")
    check("long castle", castle_move >= 0 and castle_of(castle_move) == 2)
    make(castle, castle_move)
    check("rook followed king", castle["board"][parse_sq("d1")] == 4 and castle["board"][parse_sq("c1")] == 6)

    promo = parse_fen("k7/4P3/8/8/8/8/8/4K3 w - - 0 1")
    queen = find_move(promo, "e7", "e8", 5)
    check("promotion", queen >= 0)
    make(promo, queen)
    check("became queen", promo["board"][parse_sq("e8")] == 5)

    stale = parse_fen("k7/2Q5/8/8/8/8/8/7K b - - 0 1")
    stale_king = find_king(stale["board"], stale["side"])
    check("stalemate", len(legal(stale)) == 0 and not attacked(stale["board"], stale_king, -stale["side"]))

    if errors:
        print("FAILED: " + ", ".join(errors))
        return 1
    print("ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
