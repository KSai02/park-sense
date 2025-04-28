import QRCode from 'qrcode';

export const generateQRCode = async (data) => {
  try {
    const url = await QRCode.toDataURL(data);
    return url;
  } catch (err) {
    console.error(err);
    throw new Error('QR Code generation failed');
  }
};
