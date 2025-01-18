import 'package:flutter/material.dart';
import 'api_service.dart';
import 'message.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late List<Message> _messages = [];
  final ApiService _apiService = ApiService(baseUrl: 'http://localhost:8080');
  final TextEditingController _textController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _fetchMessages();
  }

  Future<void> _fetchMessages() async {
    try {
      final messages = await _apiService.fetchMessages();
      setState(() {
        _messages = messages;
      });
    } catch (e) {
      print('Failed to fetch messages: $e');
    }
  }

  Future<void> _sendMessage() async {
    final text = _textController.text;
    if (text.isNotEmpty) {
      try {
        await _apiService.sendMessage(text);
        _textController.clear();
        _fetchMessages(); // Refresh messages after sending
      } catch (e) {
        print('Failed to send message: $e');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Home'),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                return ListTile(
                  title: Text(_messages[index].text),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _textController,
                    decoration: const InputDecoration(
                      hintText: 'Enter a message',
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: _sendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
