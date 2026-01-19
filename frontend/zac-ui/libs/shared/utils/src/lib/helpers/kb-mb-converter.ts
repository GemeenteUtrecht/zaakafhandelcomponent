export const convertKbToMb = (fileSize: number, decimals: number = 1): number => {
  const fileSizeMb = fileSize / 1000;
  return parseFloat(fileSizeMb.toFixed(decimals));
}

