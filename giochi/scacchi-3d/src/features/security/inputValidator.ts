export class InputValidator {
  public static isValidBoardCoordinate(row: number, col: number): boolean {
    return (
      Number.isInteger(row) &&
      Number.isInteger(col) &&
      row >= 0 &&
      row <= 7 &&
      col >= 0 &&
      col <= 7
    );
  }

  public static isValidColor(color: unknown): color is 'white' | 'black' {
    return color === 'white' || color === 'black';
  }

  public static isValidPieceType(
    type: unknown
  ): type is 'pawn' | 'rook' | 'knight' | 'bishop' | 'queen' | 'king' {
    return (
      typeof type === 'string' &&
      ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'].includes(type)
    );
  }

  public static clampVector3(
    val: number,
    min: number,
    max: number
  ): number {
    if (Number.isNaN(val) || !Number.isFinite(val)) return min;
    return Math.max(min, Math.min(max, val));
  }
}
