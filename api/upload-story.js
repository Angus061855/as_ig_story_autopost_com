import { Client } from '@notionhq/client';

const notion = new Client({ auth: process.env.NOTION_TOKEN });

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { imageUrls, fileNames } = req.body;

    if (!imageUrls || imageUrls.length === 0) {
      return res.status(400).json({ error: '沒有圖片 URL' });
    }

    // 每張圖各自建一筆 Notion 資料
    for (let i = 0; i < imageUrls.length; i++) {
      await notion.pages.create({
        parent: { database_id: '344c699d3b59801a9c01d7d074633983' },
        properties: {
          主題: {
            title: [{ text: { content: fileNames?.[i] || `限時動態-${i + 1}` } }]
          },
          圖片: {
            files: [
              {
                name: fileNames?.[i] || `story-${i + 1}.jpg`,
                external: { url: imageUrls[i] }
              }
            ]
          },
          狀態: {
            status: { name: '待發' }
          }
        }
      });
    }

    return res.status(200).json({ success: true, count: imageUrls.length });

  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: err.message });
  }
}

export const config = {
  api: { bodyParser: true }
};
