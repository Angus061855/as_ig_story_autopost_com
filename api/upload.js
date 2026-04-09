import { v2 as cloudinary } from 'cloudinary';
import { Client } from '@notionhq/client';
import formidable from 'formidable';

export const config = {
  api: {
    bodyParser: false,
  },
};

cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
});

const notion = new Client({ auth: process.env.NOTION_TOKEN });

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const form = formidable({ multiples: true, keepExtensions: true });

  form.parse(req, async (err, fields, files) => {
    if (err) {
      return res.status(500).json({ error: '解析失敗' });
    }

    try {
      const caption = Array.isArray(fields.caption) ? fields.caption[0] : fields.caption || '';

      let imageFiles = files.images;
      if (!imageFiles) return res.status(400).json({ error: '請選擇圖片' });
      if (!Array.isArray(imageFiles)) imageFiles = [imageFiles];

      // 照順序上傳到 Cloudinary
      const uploadedUrls = [];
      for (let i = 0; i < imageFiles.length; i++) {
        const file = imageFiles[i];
        const result = await cloudinary.uploader.upload(file.filepath, {
          folder: 'ig-posts',
          public_id: `post_${Date.now()}_${i + 1}`,
        });
        uploadedUrls.push(result.secure_url);
      }

      // 寫入 Notion
      await notion.pages.create({
        parent: { database_id: process.env.NOTION_DATABASE_ID },
        properties: {
          '文案': {
            title: [{ text: { content: caption } }],
          },
          '圖片': {
            // Files 類型：每張圖片一個 external 物件
            files: uploadedUrls.map((url, i) => ({
              name: `image_${i + 1}`,
              type: 'external',
              external: { url },
            })),
          },
          '狀態': {
            // Status 類型（不是 select）
            status: { name: '待發' },
          },
        },
      });

      return res.status(200).json({
        success: true,
        message: `上傳成功！共 ${uploadedUrls.length} 張`,
        images: uploadedUrls,
      });

    } catch (error) {
      console.error(error);
      return res.status(500).json({ error: '上傳失敗：' + error.message });
    }
  });
}
