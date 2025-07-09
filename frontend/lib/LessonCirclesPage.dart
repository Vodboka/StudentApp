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
    _fetchLessonListAndUpdateState();
  }

  Future<void> _fetchLessonListAndUpdateState() async {
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
              // IMPORTANT: Ensure percentage is handled as a double.
              // If backend sends integer 100, it might be decoded as int,
              // so explicitly convert to double if necessary.
              final percentage = (item['percentage'] is int)
                  ? (item['percentage'] as int).toDouble()
                  : item['percentage'] as double;

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

          tempOrderedNumbers.sort(); // Ensure lessons are sorted for sequential check

          setState(() {
            _orderedLessonNumbers = tempOrderedNumbers;
            _lessonData = tempLessonData;
            isLoading = false;
          });

          // --- ADDED DEBUG PRINTS ---
          print('--- DEBUGGING LESSON DATA (After setState) ---');
          _lessonData.forEach((key, value) {
            print('Lesson $key: Percentage $value% (Type: ${value.runtimeType})');
          });
          print('Is Lesson 0 completed (based on frontend logic)? ${_isLessonCompleted(0)}');
          print('Is Lesson 1 completed (based on frontend logic)? ${_isLessonCompleted(1)}');
          print('---------------------------------------------');
          // --- END DEBUG PRINTS ---

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

  // Helper function to check if a lesson is considered "completed"
  bool _isLessonCompleted(int lessonNumber) {
    // Check if the lesson exists in our data and its percentage is 100.0 or very close
    // Using a small epsilon for floating point comparison or just >= 100.0
    return _lessonData.containsKey(lessonNumber) && _lessonData[lessonNumber] != null && _lessonData[lessonNumber]! >= 75.0;
  }

  @override
  Widget build(BuildContext context) {
    // Determine if Lesson 0 is completed (needed for Lesson 1 unlock)
    final bool isLesson0Completed = _isLessonCompleted(0);
    // Determine if Lesson 1 is completed (needed for Lessons 2+ unlock)
    final bool isLesson1Completed = _isLessonCompleted(1);


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
                          onPressed: _fetchLessonListAndUpdateState,
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
                  : SingleChildScrollView(
                      child: Center(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: _orderedLessonNumbers.map((lessonNumber) {
                              final double? actualPercentage = _lessonData[lessonNumber];

                              // --- Unlocking Logic ---
                              bool isLessonAvailable;
                              if (lessonNumber == 0) {
                                isLessonAvailable = true; // Lesson 0 is always available
                              } else if (lessonNumber == 1) {
                                isLessonAvailable = isLesson0Completed; // Lesson 1 unlocks if Lesson 0 is 100%
                              } else {
                                // Lessons 2 and beyond unlock if Lesson 1 is 100%
                                isLessonAvailable = isLesson1Completed;
                              }

                              // --- Percentage Display Logic ---
                              String displayPercentageText = '';
                              Color displayPercentageColor;

                              if (actualPercentage != null) {
                                if (lessonNumber == 0) {
                                  // For Lesson 0, always display actual percentage
                                  displayPercentageText = '${actualPercentage.toStringAsFixed(0)}%';
                                } else {
                                  // For other lessons, display 0% if < 50%, else actual
                                  displayPercentageText = actualPercentage >= 50.0
                                      ? '${actualPercentage.toStringAsFixed(0)}%'
                                      : '0%';
                                }
                                displayPercentageColor = isLessonAvailable ? Colors.deepOrange : Colors.grey.shade600;
                              } else {
                                // If percentage is null (e.g., lesson not started), show 0%
                                displayPercentageText = '0%';
                                displayPercentageColor = isLessonAvailable ? Colors.deepOrange : Colors.grey.shade600;
                              }


                              return Padding(
                                padding: const EdgeInsets.symmetric(vertical: 8.0),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    GestureDetector(
                                      // Only allow tap if the lesson is available
                                      onTap: isLessonAvailable
                                          ? () async {
                                              await Navigator.push(
                                                context,
                                                MaterialPageRoute(
                                                  builder: (context) => StartLesson(
                                                    lessonNumber: lessonNumber,
                                                    hash: widget.hash,
                                                  ),
                                                ),
                                              );
                                              // After StartLesson finishes and pops, refresh the list
                                              _fetchLessonListAndUpdateState();
                                            }
                                          : null, // Set onTap to null to disable interaction
                                      child: CircleAvatar(
                                        radius: 30,
                                        backgroundColor: isLessonAvailable
                                            ? Colors.deepOrangeAccent // Active color
                                            : Colors.grey.shade400, // Greyed out for unavailable
                                        child: Text(
                                          '${lessonNumber + 1}',
                                          style: TextStyle(
                                              color: isLessonAvailable ? Colors.white : Colors.white70,
                                              fontSize: 18,
                                              fontWeight: FontWeight.bold),
                                        ),
                                      ),
                                    ),
                                    SizedBox(width: 10),
                                    Text(
                                      displayPercentageText,
                                      style: TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold,
                                          color: displayPercentageColor),
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