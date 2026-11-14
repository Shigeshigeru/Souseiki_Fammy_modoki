# 創世機ファミーモドキ(令和最新版)    

かつて存在した創世機ファミーの機能にカセットのゲームを  
ディスクシステムに変換する機能がついていました  

その機能のみを再現する試みです(インチキ   
**創世機ファミー無しで動作するのが最大の特徴です！！凄い！！**  
(変換しているので当たり前といえば当たり前なのですが  

現状でも関連資料は残されているので~~自力変換は可能なのですが~~  
AIのサポートなしでは無理レベルでした・・・(´･д･`)  
人力だとかなり大変なのでAIに手伝ってもらいながら  
自分もお勉強して変換プログラムを完成させるのが目標です  

**完成するまでツールは公開されません！！  
首を長くしてお待ちください  
お布施があれば早く完成します**  

モドキなので最終的にファイル名はRQT001Aみたいになりますが  
**本物とは全く互換性はありません**(わざわざ再現しなくてもいい  
現状は自分の確認のためカセットのゲーム名から取っています　　

最初に指定するの忘れていたためFDS内部のファイル名に  
8文字以上使おうとして失敗していました  
(いっきはikkiなので文字数が少なくて問題なかったようです  

いっきβ Ver    
<img width="526" height="120" alt="スクリーンショット 2026-11-12 205445" src="https://github.com/user-attachments/assets/f0d6d33c-39e0-4f0d-ab27-acfad0921653" />  
バトルシティーβ Ver  
<img width="527" height="126" alt="スクリーンショット 2026-11-13 003846" src="https://github.com/user-attachments/assets/56d2c876-45bc-4ec1-8852-e5dcd93843fb" />

「いっき」動作しました(AVファミコン実機とFDSkeyでも動作確認)  

<img width="301" height="240" alt="Ikki_FDS (4)_001" src="https://github.com/user-attachments/assets/7cc35e61-66bd-42b1-9889-75c4c8ebb8b1" />  
<img width="301" height="240" alt="Ikki_FDS (4)_002" src="https://github.com/user-attachments/assets/41745f50-7efa-41d2-b26c-8d362fb9ae7a" />  
<img width="301" height="240" alt="Ikki_FDS (4)_003" src="https://github.com/user-attachments/assets/33c9b805-3048-4a8a-848e-76c32ea015bc" />  
<img width="301" height="240" alt="Ikki_FDS (4)_004" src="https://github.com/user-attachments/assets/23c57955-9d8d-49eb-a3bd-343f6204eecb" />  

**バトルシティーも動作しました！！(序盤の動作確認のみ)**  

<img width="301" height="240" alt="BattleCity_FDS_005" src="https://github.com/user-attachments/assets/87312b69-7519-451d-ac9a-8bd271582806" />
<img width="301" height="240" alt="BattleCity_FDS_007" src="https://github.com/user-attachments/assets/73bf58de-c1ad-4d64-83f6-8d182524e02f" />
<img width="301" height="240" alt="BattleCity_FDS_009" src="https://github.com/user-attachments/assets/81028e30-a1f4-4b27-8d54-e39ac5e0b8d1" />

こちらは少し複雑だったようです  
一応動作確認はしましたが自分は特に問題感じませんでした  
バルーンファイトもバトルシティーと同じ位置にプログラムがあり  
BIOSと重なるのでその辺りを移動変更させての動作の模様です  

**バルーンファイトも動くようになりました！**  
<img width="301" height="240" alt="BalloonFight_FDS_001" src="https://github.com/user-attachments/assets/53a2ef05-8746-4e08-a113-4cfa4a96be25" />
<img width="301" height="240" alt="BalloonFight_FDS_002" src="https://github.com/user-attachments/assets/344f365b-09c7-49f2-b84f-408fff6bdb62" />
<img width="301" height="240" alt="BalloonFight_FDS_003" src="https://github.com/user-attachments/assets/3d178ad9-4394-40b3-ab13-4d63ece9aacc" />

バルーンファイトは簡単だと思ってたのですが  
そんなこともなかったです  
バルーントリップ修正しました

コレでA面バトルシティー、B面バルーンファイトの変換は  
できるようになったので動作確認をやっておきます　　

**キン肉マンマッスルタッグマッチもとりあえず動くようになりました！**  
<img width="256" height="240" alt="Kinnikuman_FDS_001" src="https://github.com/user-attachments/assets/5a188d79-02dc-4dd3-9f07-9bd40b87ff49" />
<img width="256" height="240" alt="Kinnikuman_FDS_002" src="https://github.com/user-attachments/assets/e58f29bd-7489-4c06-a26d-700c924a8b57" />
<img width="256" height="240" alt="Kinnikuman_FDS_003" src="https://github.com/user-attachments/assets/9226d5fb-862b-4d24-8f36-eb474a35cefe" />  
これを足掛けにキン肉マンマッスルハックマッチ(ハック)も動作するようにします  

## **対応予定とか**    
~~**A面バトルシティー、B面バルーンファイトの  
テンプレートも用意しておきます！！(コレは絶対必須)**~~    
FDSヘッダなしでの出力にも対応するので  
FDSヘッダなしで出力後  
コマンドラインで`copy /b bcity.fds + bfight.fds battlefight.fds`で大丈夫と思います  
そもそもFDSヘッダ(FDSで始まるやつ)は意味があったのでしょうか？(今となっては謎  
あぁ、前編と後編を合体させたやつとかエミュレーターでは
必要になることもありますなぁ・・・(´･д･`)
今回のは関係ないのでFDSヘッダなしで統一します  

バルトロンは個人的に必須なので対応予定  
容量の小さいものからやっていきます  
A面ツインビー、B面いっきのテンプレートに関してはカセット版の  
ツインビーの単純変換できないはずなので無理です  
正規のツインビーディスクシステム版のB面にいっきを書き込んでください  
~~A面ボンバーマン、B面シティコネクションも同様です~~  
シティコネクションはマッパー0ではなかったので  
別リポジトリでマッパー0に変換できるかとかやっておきます  
キン肉マンマッスルハックマッチはこちら(パッチです)    
https://vimm.net/romhacking/hacks/4872  
**正規にディスクシステムに移植されたものは対応しません**  
カセット版と仕様が違うタイトルは別ですが後回しになります    

# **対応済み(100%の動作を保証するものではありません)**  
(FDS名は暫定です)  

いっき (ikkij_FDS.fds)  
バトルシティー (bcityj_FDS.fds)    
バルーンファイト (bfightj_FDS.fds)  
キン肉マンマッスルタッグマッチ (とりあえず対応)

# **不明点、気になること、仕様**  
自分はディスクシステムBIOSやゲームを自分で吸い出しているので  
問題はないのですがKYODAKU-.00の問題があるので  
**最終的には実行、作成には何かしらの  
公式ディスクゲームイメージ(FDS形式、ゲームの種類は問いません    
ファイルが一部壊れているものでも使えるところが生きていれば可)を  
用意してください  
QDからFDSに変換するツール等があるので  
実ディスクを吸い出さなくても何かしらのメディアから  
取り出せられるかもしれません(  
KYODAKU-.00は毎回同じ物が使用されていたり  
Homebrew作品でも同じCRCのものが公開されているので  
BIOSは必須にしないでおこうと思いましたが  
実装の都合と著作権の問題的にそっちのほうが楽なのでやっぱりそうします  
(エミュレーターでは必須なので文句は言わせません)  
片面単位で変換するのでA面B面の識別はありません  
(この実装でも動作するはずなので直す予定はありません)  
変換用NROMイメージはCHR部分は改変されていても  
恐らく問題ないはずですがPRG部分はバージョン違いや改変が  
あると多分変換できません  
ヘッダ付きのNROMを変換してるのですが吸い出し時の  
ヘッダ作成時に垂直(Vertical)と水平(Horizontal)を  
間違えてるものが結構ある気がします  
めんどくさいですが資料にて確認してから作業します  
ディスクシステムにおいてはカセットの  
基板のように物理的に判別はできないため必要です  
変換用のNROMイメージに関しても  
別メディアからなんとかかんとか(お察しください  
改変やバージョン違いに関しては基本的に対応はしません  
<img width="301" height="240" alt="Battle_City_jp_001" src="https://github.com/user-attachments/assets/d7544667-00e4-45fc-9f6d-e1de4a87d954" />  
下記にも書いていますがNROM(マッパー0)以外の  
変換は無理です**
  
# **大事なこと**    
AI無料枠で作業するのでとても時間がかかります    
お気持ち程度のマネーの寄付があればプラン変更して  
作業は早くなると思います  
但し個人の趣味、研究、道楽として作っているので  
完成度に関しては期待しないでください  
実ディスク、実機でも確認予定ですが  
実ディスク使用するとディスクID等が  
書き換えられ全てでっち上げID等となるはずです  
**大事なディスクはバックアップしておいてください**  
**動作するROMは創世機ファミーと同じものです  
NROM最大PRG-ROM 32KB＋CHR-ROM 8KB**(多分  

参考サイト  
https://www.nesdev.org/wiki/Souseiki_Fammy  
https://www.nesdev.org/wiki/NROM  
https://forums.nesdev.org/viewtopic.php?t=26064  

マッパー0(NROM)のリスト(もっとあるはずです)    
https://nesdir.github.io/mapper0.html  
https://datacrystal.tcrf.net/wiki/Category:NES_games_using_mapper_number_0

BAKUTEDOさんの創世機ファミーの記事(分かりやすい！！)  
https://bakutendo.net/blog-entry-415.html

### シティコネクションのマッパーの件(別リポジトリで使用すると思います)  

マッパーハックの参考サイト(シティコネクション、ツインビーに言及ありました)    
https://bootleggames.fandom.com/wiki/Mapper_hack

シティコネクションのマッパーの件  
https://nicole.express/2024/city-disconnection.html

全然関係ない話で恐縮ですがRetroBitのマルチカート吸い出し  
無理かと思ってたのですがもしかしてできるのかもしれません  
コレはコレで調べておきます  
無理やりNAND(?)から吸い出す方法もありますが普通は無理です

