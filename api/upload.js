import { Client } from '@notionhq/client';

const notion = new Client({ auth: process.env.NOTION_TOKEN });

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { imageUrls, caption } = req.body;

    if (!imageUrls || imageUrls.length === 0) {
      return res.status(400).json({ error: '沒有圖片 URL' });
    }

    await notion.pages.create({
      parent: { database_id: process.env.NOTION_DATABASE_ID },
      properties: {
        Name: {
          title: [{ text: { content: caption.slice(0, 50) || '新貼文' } }]
        },
        Caption: {
          rich_text: [{ text: { content: caption } }]
        },
        Images: {
          files: imageUrls.map((url, i) => ({
            name: `image-${i + 1}.jpg`,
            external: { url }
          }))
        },
        Status: {
          select: { name: '待發佈' }
        }
      }
    });

    return res.status(200).json({ success: true });

  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: err.message });
  }
}

export const config = {
  api: { bodyParser: true }
};
