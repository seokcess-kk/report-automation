import { NextResponse } from 'next/server';
import { getBranchAdgroups, getCreativeAds } from '@/lib/action-executor';

/** 실행 전 모달에서 사용:
 *   ?branch=서울  -> adgroup 리스트
 *   ?creative=... -> ad 리스트
 */
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const branch = searchParams.get('branch');
  const creative = searchParams.get('creative');

  if (branch) {
    const adgroups = await getBranchAdgroups(branch);
    return NextResponse.json({ adgroups });
  }
  if (creative) {
    const ads = await getCreativeAds(creative);
    return NextResponse.json({ ads });
  }
  return NextResponse.json({ error: 'branch 또는 creative 파라미터 필요' }, { status: 400 });
}
