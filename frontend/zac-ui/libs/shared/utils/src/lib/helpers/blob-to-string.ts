export const convertBlobToString = (file: File): Promise<string | ArrayBuffer> => {
  // Convert Blob to base64 encoded string
  const reader = new FileReader();
  reader.readAsDataURL(file);
  return new Promise(resolve => {
    reader.onload = () => {
      resolve (reader.result)
    }
    reader.onerror = () => {
      console.log('File upload failed')
    }
  })
}

