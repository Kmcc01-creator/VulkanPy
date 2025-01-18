class Message {
  final String text;

  Message({required this.text});

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      text: json['text'],
    );
  }
}
