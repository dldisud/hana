// chzzk_bridge.js
// @d2n0s4ur/chzzk-chat 패키지를 사용하여 치지직 채팅을 읽는 브릿지 스크립트

const { ChzzkChat } = require("@d2n0s4ur/chzzk-chat");

// 채널 ID를 인자로 받음
const channelId = process.argv[2];

if (!channelId) {
  console.error("사용법: node chzzk_bridge.js <채널ID>");
  process.exit(1);
}

// ChzzkChat 인스턴스 생성
const chzzkChat = new ChzzkChat(channelId);

// 채팅 메시지 핸들러
const messageHandler = ({
  badges,
  nick,
  message
}) => {
  // 채팅 메시지를 JSON 형식으로 출력
  const chatData = {
    type: "chat",
    username: nick,
    message: message,
    badges: badges,
    timestamp: Date.now(),
    platform: "chzzk"
  };
  
  console.log(JSON.stringify(chatData));
};

// 도네이션 핸들러
const donationHandler = ({
  badges,
  nick,
  message,
  isAnonymous,
  amount
}) => {
  // 도네이션 메시지를 JSON 형식으로 출력
  const donationData = {
    type: "donation",
    username: isAnonymous ? "익명" : nick,
    message: message,
    amount: amount,
    badges: badges,
    isAnonymous: isAnonymous,
    timestamp: Date.now(),
    platform: "chzzk"
  };
  
  console.log(JSON.stringify(donationData));
};

// 구독 핸들러
const subscriptionHandler = ({
  badges,
  nick,
  message,
  month,
  tierName,
  tierNo
}) => {
  // 구독 메시지를 JSON 형식으로 출력
  const subscriptionData = {
    type: "subscription",
    username: nick,
    message: message,
    month: month,
    tierName: tierName,
    tierNo: tierNo,
    badges: badges,
    timestamp: Date.now(),
    platform: "chzzk"
  };
  
  console.log(JSON.stringify(subscriptionData));
};

// 핸들러 등록
chzzkChat.addMessageHandler(messageHandler);
chzzkChat.addDonationHandler(donationHandler);
chzzkChat.addSubscriptionHandler(subscriptionHandler);

// 프로세스 종료 시 웹소켓 연결 종료
process.on('SIGINT', () => {
  console.error("프로그램을 종료합니다...");
  chzzkChat.close();
  process.exit(0);
});

// 표준 입력 처리 (명령어 수신)
process.stdin.on('data', (data) => {
  const input = data.toString().trim();
  
  if (input === 'exit' || input === 'quit') {
    console.error("프로그램을 종료합니다...");
    chzzkChat.close();
    process.exit(0);
  }
});

console.error(`채널 ID ${channelId}의 치지직 채팅 연결을 시작합니다...`);
