// ignore_for_file: file_names

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'StartLesson.dart'; // Ensure this file exists and is correctly implemented

class LessonService {
  static const String baseUrl = 'http://10.0.2.2:5000'; // Ensure this matches your backend's IP and port

  Future<List<Map<String, dynamic>>?> fetchQuestions(String hash, int lessonNumber) async {
    final uri = Uri.parse('$baseUrl/get_lesson_questions')
        .replace(queryParameters: {
      'hash': hash,
      'lesson_number': lessonNumber.toString(),
    });

    try {
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final questions = data['questions'];

        if (questions is List) {
          return questions
              .map<Map<String, dynamic>>((item) => Map<String, dynamic>.from(item))
              .toList();
        } else {
          print('Unexpected response format for questions for lesson $lessonNumber: $data');
          return null;
        }
      } else {
        print('Error fetching lesson questions for lesson $lessonNumber: Status ${response.statusCode}, Body: ${response.body}');
        return null;
      }
    } catch (e) {
      print('Network error fetching lesson questions for lesson $lessonNumber: $e');
      return null;
    }
  }
}

class LessonCirclesPage extends StatefulWidget {
  final String hash;

  LessonCirclesPage({required this.hash});

  @override
  _LessonCirclesPageState createState() => _LessonCirclesPageState();
}

class _LessonCirclesPageState extends State<LessonCirclesPage> {
  Map<int, double> _lessonData = {};
  List<int> _orderedLessonNumbers = [];

  bool isLoading = true;
  bool hasError = false;
  String errorMessage = "";

  @override
  void initState() {
    super.initState();
    print("LessonCirclesPage: Initializing with hash: ${widget.hash}");
    fetchLessonList();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    fetchLessonList();
  }

  Future<void> fetchLessonList() async {
    setState(() {
      isLoading = true;
      hasError = false;
      errorMessage = "";
      _lessonData.clear();
      _orderedLessonNumbers.clear();
    });

    final url = Uri.parse('http://10.0.2.2:5000/get_lessons_for_hash?hash=${widget.hash}');
    print("LessonCirclesPage: Attempting to fetch lesson list from URL: $url");

    try {
      final response = await http.get(url);
      print("LessonCirclesPage: Response Status Code: ${response.statusCode}");
      print("LessonCirclesPage: Response Body: ${response.body}");

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data.containsKey('lessons') && data['lessons'] is List) {
          List<int> tempOrderedNumbers = [];
          Map<int, double> tempLessonData = {};

          for (var item in data['lessons']) {
            if (item is Map<String, dynamic> && item.containsKey('lesson_number') && item.containsKey('percentage')) {
              final lessonNum = item['lesson_number'];
              final percentage = item['percentage'];

              if (lessonNum is int && percentage is double) {
                tempOrderedNumbers.add(lessonNum);
                tempLessonData[lessonNum] = percentage;
              } else {
                print('Warning: Invalid type for lesson_number or percentage in item: $item');
              }
            } else {
              print('Warning: Unexpected item format in lessons list: $item');
            }
          }

          tempOrderedNumbers.sort();

          setState(() {
            _orderedLessonNumbers = tempOrderedNumbers;
            _lessonData = tempLessonData;
            isLoading = false;
          });

        } else {
          setState(() {
            hasError = true;
            isLoading = false;
            errorMessage = "Invalid data format from server: 'lessons' key missing or not a list.";
            print("LessonCirclesPage Error: $errorMessage");
          });
        }
      } else {
        setState(() {
          hasError = true;
          isLoading = false;
          errorMessage = 'Failed to load lesson list. Status: ${response.statusCode}, Body: ${response.body}';
          print("LessonCirclesPage Error: $errorMessage");
        });
      }
    } catch (e) {
      print("LessonCirclesPage Network Error: $e");
      setState(() {
        hasError = true;
        isLoading = false;
        errorMessage = 'Network error or server unreachable: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Lessons for ${widget.hash}')),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : hasError
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          "Error loading lessons:",
                          style: TextStyle(fontSize: 18, color: Colors.red),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: 10),
                        Text(
                          errorMessage,
                          style: TextStyle(fontSize: 14, color: Colors.redAccent),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: 20),
                        ElevatedButton(
                          onPressed: fetchLessonList,
                          child: Text("Retry"),
                        ),
                      ],
                    ),
                  ),
                )
              : _orderedLessonNumbers.isEmpty
                  ? Center(
                      child: Text(
                        "No lessons found for this hash. Please add lessons or check the hash.",
                        style: TextStyle(fontSize: 16, color: Colors.grey[700]),
                        textAlign: TextAlign.center,
                      ),
                    )
                  : SingleChildScrollView( // <--- Wrap with SingleChildScrollView
                      child: Center(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: _orderedLessonNumbers.map((lessonNumber) {
                              final percentage = _lessonData[lessonNumber];

                              return Padding(
                                padding: const EdgeInsets.symmetric(vertical: 8.0),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    GestureDetector(
                                      onTap: () {
                                        Navigator.push(
                                          context,
                                          MaterialPageRoute(
                                            builder: (context) => StartLesson(
                                              lessonNumber: lessonNumber,
                                              hash: widget.hash,
                                            ),
                                          ),
                                        );
                                      },
                                      child: CircleAvatar(
                                        radius: 30,
                                        backgroundColor: Colors.deepOrangeAccent,
                                        child: Text(
                                          '${lessonNumber + 1}',
                                          style: TextStyle(
                                              color: Colors.white,
                                              fontSize: 18,
                                              fontWeight: FontWeight.bold),
                                        ),
                                      ),
                                    ),
                                    SizedBox(width: 10),
                                    if (percentage != null)
                                      Text(
                                        '${percentage.toStringAsFixed(0)}%',
                                        style: TextStyle(
                                            fontSize: 18,
                                            fontWeight: FontWeight.bold,
                                            color: Colors.deepOrange),
                                      )
                                    else
                                      SizedBox(
                                        width: 20,
                                        height: 20,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          valueColor: AlwaysStoppedAnimation<Color>(Colors.deepOrange),
                                        ),
                                      ),
                                  ],
                                ),
                              );
                            }).toList(),
                          ),
                        ),
                      ),
                    ),
    );
  }
}
